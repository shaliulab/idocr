# Standard library imports
import datetime
import logging
import os.path

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
from learnmem.server.roi_builders.target_roi_builder import IDOCROIBuilder
from learnmem.server.drawers.drawers import DefaultDrawer

logger = logging.getLogger(__name__)

class ControlThread(Base, Root):
    r"""
    A class to orchestrate the communication between the server
    and all the IDOC modules
    """

    _option_dict = {

        'roi_builder': {
            'possible_classes': [
                IDOCROIBuilder
            ],
            'default_class': IDOCROIBuilder
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


    def __init__(self, machine_id, version, result_dir, experiment_data, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._settings = {"adaptation_time": 0}
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
        self.mapping_path = experiment_data["mapping_path"] or self._config.content['controller']['mapping_path']  # pylint: disable=line-too-long
        self.program_path = experiment_data["program_path"]
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

    # @property
    # def adaptation_time(self):
    #     return self._settings['adaptation_time']

    def logs(self):
        return {"logs": []}

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
        r"""
        """

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


    def load_program(self, program_path):
        self.controller.load_program(program_path)

    def list_programs(self):
        # TODO remove me
        logger.info("Running controller.list()")
        return self.controller.list()


    @property
    def video_out(self):
        if self._video_path is None:
            self._video_out = filename = self.start_datetime + '_idoc_' + get_machine_id() + ".csv"
            self._video_out = os.path.join(
                self.result_writer.result_dir,
                filename
            )
        else:
            self._video_out = self._video_path

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
        if submodule == 'control_thread':
            instance = self
        else:
            instance = self._submodules[submodule]

        if action in ['run', 'stop']:
            getattr(instance, action)()
        elif action in ['ready']:
            setattr(instance, action, True)

        elif action == "start":
            instance.run()

        else:
            logger.info("Action %s is not valid. Please select one in [run, stop ready].", action)


        return self.status


    def start_result_writer(self):
        logger.info('Starting result writer')
        result_writer_class = self._option_dict['result_writer']['default_class']
        result_writer_args = self._config.content['io']['result_writer']['args']
        result_writer_kwargs = self._config.content['io']['result_writer']['kwargs']

        self.result_writer = result_writer_class(
            start_datetime= self.start_datetime,
            *result_writer_args,
            **result_writer_kwargs
        )


    def start_controller(self):
        logger.debug('Starting controller')
        self.controller = Controller(
            mapping_path=self.mapping_path,
            program_path=self.program_path,
            board_name=self.board_name,
            arduino_port=self.arduino_port
        )
        self._settings.update(self.controller.settings)


    def start_recognizer(self):
        logger.debug('Starting recognizer function')

        roi_builder_class = self._option_dict["roi_builder"]['default_class']

        roi_builder = roi_builder_class()

        tracker_class = self._option_dict['tracker']['default_class']
        camera_class_name = self._config.content['io']['camera']['class']

        for cls in self._option_dict['camera']['possible_classes']:
            if camera_class_name == cls.__name__:
                camera_class = cls

        self._option_dict['camera']['default_class']
        drawer_class = self._option_dict['drawer']['default_class']

        camera_args = self._config.content['io']['camera']['args']
        camera_kwargs = self._config.content['io']['camera']['kwargs']

        camera = camera_class(*camera_args, **camera_kwargs)

        drawer_args = self._config.content['drawer']['args']
        drawer_kwargs = self._config.content['drawer']['kwargs']
        drawer = drawer_class(*drawer_args, video_out=self.video_out, **drawer_kwargs)

        try:
            rois = roi_builder.build(camera)
        except Exception as error:
            logger.warning(error)
            roi_builder_class = DefaultROIBuilder
            roi_builder = roi_builder_class()
            rois = roi_builder.build(camera)

        self.recognizer = Recognizer(camera, tracker_class, self.result_writer, drawer, rois=rois)
        self.recognizer.start()


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
            # TODO check next frame has come!

            try:
                pass
                # print("")
                # shape = self.last_drawn_frame.shape
                # print("Shape %s" % " ".join([str(e) for e in shape]))

            except AttributeError as error:
                logger.warning(error)

            self._end_event.wait(1/self.sampling_rate)

        return

    def stop(self):
        r"""
        Respond to user input by stopping all dependent modules.
        and setting your status to stopped.
        """

        super().stop()
        if self.recognize:
            self.recognizer.stop()

        if self.controller:
            self.controller.stop()

        self.result_writer.stop()
        return