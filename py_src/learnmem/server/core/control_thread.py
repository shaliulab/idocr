# Standard library imports
import datetime
import logging
import os.path
import traceback

# Local application imports
from learnmem.server.controllers.controllers import Controller
from learnmem.server.core.base import Base, Root
from learnmem.server.core.recognizer import Recognizer
# from learnmem.server.trackers.simple_tracker import SimpleTracker
from learnmem.server.trackers.adaptive_bg_tracker import AdaptiveBGModel
from learnmem.server.io.result_writer import CSVResultWriter
from learnmem.configuration import LearnMemConfiguration
from learnmem.helpers import get_machine_id, get_machine_name
from learnmem.server.io.pylon_camera import PylonCamera
from learnmem.server.io.opencv_camera import OpenCVCamera
from learnmem.server.roi_builders.roi_builders import DefaultROIBuilder
from learnmem.server.roi_builders.high_contrast_roi_builder import HighContrastROIBuilder
from learnmem.server.drawers.drawers import DefaultDrawer
from learnmem.server.utils.debug import IDOCException

logger = logging.getLogger(__name__)

class ControlThread(Base, Root):
    r"""
    A class to orchestrate the communication between the server
    and all the IDOC modules
    """

    _option_dict = {

        'roi_builder': {
            'possible_classes': [
                HighContrastROIBuilder, DefaultROIBuilder
            ],
            'default_class': HighContrastROIBuilder
        },

        'tracker': {
            'possible_classes': [
                #DefaultTracker,
                AdaptiveBGModel
                #AdaptiveBGModel
            ],
            'default_class': AdaptiveBGModel
        },

        'drawer': {
            'possible_classes': [
                DefaultDrawer
            ],
            'default_class': DefaultDrawer

        },

        'camera': {
            'possible_classes': [
                PylonCamera, OpenCVCamera
            ],
            'default_class': PylonCamera
        },

        'result_writer': {
            'possible_classes': [
                CSVResultWriter
            ],
            'default_class': CSVResultWriter
        }
    }

    # TODO Clean this
    _odor_a = "A" #overriden by conf and user
    _odor_b = "B" #overriden by conf and user
    sampling_rate = 50 # overriden by conf


    valid_actions = ["start", "stop", "start_experiment", "stop_experiment"]

    def __init__(self, machine_id, version, result_dir, experiment_data, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._settings = {}
        self._submodules = {}

        self.machine_id = machine_id
        self.version = version
        self._result_dir = result_dir

        # TODO: Fix this dirty init function
        self._config = LearnMemConfiguration()
        for k in self._config.content['experiment']:
            setattr(self, k, self._config.content['experiment'][k])

        ## Assignment of attributes
        self.control = experiment_data['control']
        self.recognize = experiment_data['recognize']
        self.save = experiment_data['save']

        # self.reporting = experiment_data["reporting"]
        self.camera_name = experiment_data["camera"]
        self._video_path = experiment_data["video_path"]
        self._video_out = None
        self.mapping_path = experiment_data["mapping_path"] or self._config.content['controller']['mapping_path']  # pylint: disable=line-too-long
        self.paradigm_path = experiment_data["paradigm_path"]
        self.output_path = experiment_data["output_path"]
        self.arduino_port = experiment_data["arduino_port"]
        self.board_name = experiment_data["board_name"] or self._config.content['controller']['board_name'] # pylint: disable=line-too-long
        self.experimenter = experiment_data["experimenter"]
        self._status = {}

        logger.info("Start time: %s", datetime.datetime.now().isoformat())


    @property
    def info(self):
        return self._info

    @info.getter
    def info(self):

        # logger.debug('Control thread is updating the info')
        status = 'offline'

        if self.recognize:
            self._info["recognizer"] = self.recognizer.info
            status = 'running'
        else:
            self._info["recognizer"] = {"status": "offline"}

        if self.control:
            self._info["controller"] = self.controller.info
            status = 'running'

        else:
            self._info["controller"] = {"status": "offline"}

        self._info.update({
            "id": get_machine_id(),
            "location": self._config.content["experiment"]["location"],
            "name": get_machine_name(),
            "status": status

        })
        # logger.debug('ControlThread.info OK')
        return self._info

    @property
    def controlling(self):
        if self.controller is not None:
            return self.controller.status == 'running'
        return False

    @property
    def recognizing(self):
        if self.recognize is not None:
            return self.recognizer.status == 'running'
        return False

    @property
    def status(self):
        return self._status

    @status.getter
    def status(self):

        self._status.update({
            "recognizer": self.recognizing,
            "controller": self.controlling,
        })


        if not self.running:
            self._status["control_thread"] = "idle"

        elif self.ready and not self.running:
            self._status["control_thread"] = 'ready'

        elif self.running and not self.stopped:
            self._status["control_thread"] = "running"

        elif self.stopped:
            self._status["control_thread"] = "stopped"

        else:
            logger.warning('%s status undefined', self.__class__.__name__)
            self._status["control_thread"] = 'undefined'

        return self._status


    def load_paradigm(self, paradigm_path):
        self.controller.load_paradigm(paradigm_path)

    def list_paradigms(self):
        # TODO remove me
        logger.info("Running controller.list()")
        return self.controller.list()


    @property
    def video_out(self):

        filename = self.start_datetime + '_idoc_' + get_machine_id() + ".csv"
        self._video_out = os.path.join(
            self.result_writer.result_dir,
            filename
        )

        return self._video_out

    @property
    def mapping(self):
        if self.control:
            return self.controller.mapping
        return None

    @property
    def pin_state(self):
        if self.control:
            return self.controller.pin_state

    @property
    def recognizer(self):

        return self._submodules["recognizer"]

    @recognizer.setter
    def recognizer(self, recognizer):
        self._submodules["recognizer"] = recognizer
        self._settings.update(recognizer.settings)


    @property
    def controller(self):
        if self.control:
            return self._submodules["controller"]

    @controller.setter
    def controller(self, controller):
        self._submodules["controller"] = controller
        self._settings.update(controller.settings)

    @property
    def result_writer(self):
        return self._submodules["result_writer"]

    @result_writer.setter
    def result_writer(self, result_writer):
        self._submodules["result_writer"] = result_writer

    def command(self, submodule, action):
        r"""
        Control the submodules with actions
        """
        try:
            if submodule == 'control_thread':
                instance = self

            elif submodule in self._submodules:
                instance = self._submodules[submodule]
            else:
                logger.warning(
                    "Please command one of the following modules: %s",
                    " ".join(
                        ["control_thread"] + list(self._submodules.keys())
                    )
                )

            if action == "start" and instance.running:
                logger.warning("%s is already running" % instance.__class__.__name__)
                return self.status

            else:
                getattr(instance, action)()

        except Exception as error:
            logger.warning(error)
            logger.warning(traceback.print_exc())
            logger.info("Action %s is not valid. Please select one in %s.", action, ' '.join(instance.valid_actions))


        return self.status


    def start_result_writer(self):
        logger.info('Starting result writer')
        result_writer_class = self._option_dict['result_writer']['default_class']
        result_writer_args = self._config.content['io']['result_writer']['args']
        result_writer_kwargs = self._config.content['io']['result_writer']['kwargs']

        self.result_writer = result_writer_class(
            start_datetime=self.start_datetime,
            *result_writer_args,
            **result_writer_kwargs
        )


    def start_controller(self):
        logger.debug('Starting controller')
        self.controller = Controller(
            mapping_path=self.mapping_path,
            paradigm_path=self.paradigm_path,
            board_name=self.board_name,
            arduino_port=self.arduino_port
        )
        self._settings.update(self.controller.settings)


    def start_recognizer(self):
        logger.debug('Starting recognizer function')

        # Initialize camera (use the class declared in the config)
        camera_class_name = self._config.content['io']['camera']['class']
        for cls in self._option_dict['camera']['possible_classes']:
            if camera_class_name == cls.__name__:
                camera_class = cls


        # Initialize roi_builder
        roi_builder_class = self._option_dict["roi_builder"]['default_class']
        roi_builder_args = self._config.content['roi_builder']['args']
        roi_builder_kwargs = self._config.content['roi_builder']['kwargs']
        roi_builder = roi_builder_class(
            *roi_builder_args,
            **roi_builder_kwargs
        )

        # Initialize drawer
        drawer_class = self._option_dict['drawer']['default_class']
        drawer_args = self._config.content['drawer']['args']
        drawer_kwargs = self._config.content['drawer']['kwargs']
        drawer = drawer_class(
            *drawer_args,
            video_out=self.video_out,
            **drawer_kwargs
        )

        # Pick tracker class and initialize recognizer
        tracker_class = self._option_dict['tracker']['default_class']
        self.recognizer = Recognizer(
            tracker_class, camera_class, roi_builder, self.result_writer, drawer,
            start_saving=True, video_path=self._video_path
        )
        self._settings.update(self.recognizer.settings)

    def start_submodules(self):

        logger.debug("Starting submodules")
        logger.debug(self._submodules)

        self.start_result_writer()

        if self.control:
            self.start_controller()

        if self.recognize:
            self.start_recognizer()

        logger.debug(self._submodules)


    @property
    def last_drawn_frame(self):
        if self.recognize:
            return self.recognizer.drawer.last_drawn_frame
        else:
            return None

    def run(self):
        r"""
        Start all the submodules.
        """
        super().run()
        self.start_submodules()

        while not self.stopped:
            # TODO

            # # TODO check next frame has come!
            # self.recognizer.load_camera()
            # # prepare recognizer upon user input
            # self.recognizer.prepare()
            # # start recognizer upon user input
            # self.recognizer.start()
            self._end_event.wait(1/self.sampling_rate)
            if self.controller.progress > 100:
                self.stop_experiment()
                break

        return


    def stop(self):
        """
        Stop everything!
        """
        super().stop()
        self.stop_experiment()


    def start_experiment(self):
        r"""
        Convenience combination of commands targeted to start an experiment

        * The recognizer starts saving the position of the flies
        * The controller starts executing its paradigm
        """

        # set the self.start_datetime property to now with format
        # %YYYYY-MM-DD_HH-MM-SS
        self._set_start_datetime()

        # allow the result_writer to write to disk the incoming data from now on
        self.result_writer.running = True

        if self.recognize:
            if self.recognizer.running:
                # tell the recognizer it can start_saving from now on
                # please note it could alreadey be saving if start_saving=True
                # was passed at init time and the result_writer was running
                # if it was not True, then the time difference between now and when
                # the recognizer started running will be substracted in the resulting data
                # so as to align it to the controller
                self.recognizer.start_saving()
            else:
                if not self.recognizer.ready:
                    try:
                        # if the recognizer is not ready, it needs to prepare:
                        # * find the regions of interest (ROIS)
                        # * bind a tracker to each ROI
                        self.recognizer.prepare()
                    except Exception as error:
                        logger.warning("Could not prepare recognizer. Please try again")
                        logger.warning(error)
                        logger.warning(traceback.print_exc())
                        return None

                    # tell the recognizer it can start saving and the offset will be 0
                    self.recognizer.start_saving(0)

                # start tracking flies
                self.recognizer.start()

        if self.control:
            # start the paradigm loaded in the controller
            self.controller.start()

    def stop_experiment(self):
        """
        Convenience combination of commands targeted to stop an experiment.

        * The recognizer stops tracking and recording frames
        * The controller stops doing experiments
        * The result writer clears its cache

        NOTE: This does not stop the execution of ControlThread.run().
        Only the stop() method can do that.
        """

        if self.recognize:
            self.recognizer.stop()

        if self.control:
            self.controller.stop()

        self.result_writer.clear()
