# Standard library imports
import datetime
import logging
import os.path
import traceback

import pandas as pd

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
from learnmem.server.controllers.boards import ArduinoDummy, ArduinoMegaBoard, ArduinoBoard
from learnmem.server.roi_builders.target_roi_builder import IDOCROIBuilder
from learnmem.server.drawers.drawers import DefaultDrawer
from learnmem.server.utils.debug import IDOCException
from learnmem.helpers import hours_minutes_seconds, iso_format, MachineDatetime

logger = logging.getLogger(__name__)

class ControlThread(Base, Root):
    r"""
    A class to orchestrate the communication between the server
    and all the IDOC modules
    """

    _option_dict = {

        'board': {
            'possible_classes': [
                ArduinoBoard, ArduinoMegaBoard, ArduinoDummy
            ]
        },

        'camera': {
            'possible_classes': [
                PylonCamera, OpenCVCamera
            ]
        },

        'drawer': {
            'possible_classes': [
                DefaultDrawer
            ]
        },

        'result_writer': {
            'possible_classes': [
                CSVResultWriter
            ]
        },

        'roi_builder': {
            'possible_classes': [
                IDOCROIBuilder, HighContrastROIBuilder, DefaultROIBuilder
            ]
        },

        'tracker': {
            'possible_classes': [
                AdaptiveBGModel
            ]
        },

    }

    sampling_rate = 50 # overriden by conf


    valid_actions = ["start", "stop", "start_experiment", "stop_experiment"]

    def __init__(self, machine_id, version, result_dir, user_data, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if user_data["adaptation_time"] is None:
            adaptation_time = self._config.content["experiment"]["adaptation_time"]
        else:
            adaptation_time = user_data["adaptation_time"]

        self._settings.update({
            "adaptation_time": adaptation_time
        })

        self._submodules = {"recognizer": None, "controller": None, "result_writer": None}

        self.machine_id = machine_id
        self.machine_name = get_machine_name()

        self.version = version
        self._result_dir = result_dir

        self._location = self._config.content['experiment']['location']
        self._max_duration = self._config.content['experiment']['max_duration']

        ## Assignment of attributes
        self.control = user_data['control']
        self.recognize = user_data['recognize']

        # self.reporting = user_data["reporting"]
        self._user_classes = {
            "camera": user_data.pop("camera"),
            "board": user_data.pop("board"),
            "drawer": user_data.pop("drawer"),
            "result_writer": user_data.pop("result_writer"),
            "roi_builder": user_data.pop("roi_builder"),
            "tracker": user_data.pop("tracker")
        }
        self._video_out = None
        self._user_data = user_data
        self._status = {}
        logger.info("Control thread initialized")

    @property
    def selected_options(self):
        return {
            "camera": self._pick_class("camera"),
            "board": self._pick_class("board"),
            "drawer": self._pick_class("drawer"),
            "result_writer": self._pick_class("result_writer"),
            "roi_builder": self._pick_class("roi_builder"),
            "tracker": self._pick_class("tracker"),
            "controller": self.controlling,
            "recognizing": self.recognizing
        }

    @property
    def run_id(self):
        return "%s_%s" % (self._start_datetime, self.machine_id)

    @property
    def run_id_short(self):
        return "%s_%s" % (self._start_datetime, self.machine_id[:5])

    @property
    def adaptation_time(self):
        return self._settings['adaptation_time']

    @property
    def adaptation_time_human(self):
        return iso_format(
                    hours_minutes_seconds(
                        self._settings['adaptation_time']
                    )
                )


    @property
    def adaptation_offset(self):
        return max(0, self.adaptation_time - self.elapsed_seconds)

    @property
    def metadata(self):
        metadata = pd.DataFrame([
            {"field": "run_id", "value": self.run_id_short},
            {"field": "machine_id", "value": self.machine_id},
            {"field": "machine_name", "value": self.machine_name},
            {"field": "version", "value": self.version},
            {"field": "date_time", "value": self.start_datetime},
            {"field": "selected_options", "value": self.selected_options},
            {"field": "settings", "value": self.settings},
            {"field": "user_data", "value": self._user_data}
        ])

        return metadata

    @property
    def info(self):
        return self._info

    @info.getter
    def info(self):

        if self.recognize:
            self._info["recognizer"] = self.recognizer.info
        else:
            self._info["recognizer"] = {"status": "offline"}

        if self.control:
            self._info["controller"] = self.controller.info
        else:
            self._info["controller"] = {"status": "offline"}

        self._info.update({
            "id": self.machine_id,
            "location": self._location,
            "name": self.machine_name,
            "status": self.status["control_thread"],
            "submodules": {k: self.status[k] for k in self._submodules},
            "clock": self.clock

        })

        return self._info

    @property
    def controlling(self):
        if self.controller is not None  and self.controller is not None:
            return self.controller.status == 'running'
        return False

    @property
    def recognizing(self):
        if self.recognize is not None and self.recognizer is not None:
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
            "result_writer": self.result_writer.status,
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

    def toggle(self, hardware, value):

        result = {"status": None}

        if self.controller is not None:
            try:
                self.controller.toggle(hardware, value)
                return {"status": "success"}
            except Exception as error:
                logger.warning(error)
                logger.warning(traceback.print_exc())
        return result

    @property
    def video_out(self):
        filename = self.run_id + ".avi"
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
                logger.warning("%s is already running", instance.__class__.__name__)
                return self.status

            else:
                getattr(instance, action)()

        except RuntimeError as error:
            logger.warning("%s is already started", submodule)

        except Exception as error:
            logger.warning(error)
            logger.warning(traceback.print_exc())
            logger.info("Action %s is not valid. Please select one in %s.", action, ' '.join(instance.valid_actions))


        return self.status

    def _pick_class(self, category):
        """
        Select a class for a given category
        among those listed in the _option_dict default_class key
        for that category.
        """

        class_name = self._user_classes[category] or self._config.content['default_class'][category]

        for cls in self._option_dict[category]['possible_classes']:
            if class_name == cls.__name__:
                return cls

        raise IDOCException("Class %s is not a possible class for category %s" % (class_name, category))

    def initialise_result_writer(self):
        logger.info('Starting result writer')
        result_writer_class = self._pick_class("result_writer")
        result_writer_args = self._config.content['io']['result_writer']['args']
        result_writer_kwargs = self._config.content['io']['result_writer']['kwargs']

        self.result_writer = result_writer_class(
            start_datetime=self.start_datetime,
            *result_writer_args,
            **result_writer_kwargs
        )


    def initialise_controller(self):
        logger.debug('Starting controller')
        self.controller = Controller(
            mapping_path=self._user_data["mapping_path"],
            paradigm_path=self._user_data["paradigm_path"],
            result_writer=self.result_writer,
            board_class=self._pick_class("board"),
            arduino_port=self._user_data["arduino_port"],
            use_wall_clock=self._user_data["use_wall_clock"],
            adaptation_offset=self.adaptation_offset
        )
        # self.controller.experiment_start = self.experiment_start
        self._settings.update(self.controller.settings)


    def initialise_recognizer(self):
        logger.debug('Starting recognizer function')

        # Initialize camera (use the class declared in the config)
        camera_class = self._pick_class("camera")

        # Initialize roi_builder
        roi_builder_class = self._pick_class("roi_builder")
        roi_builder_args = self._config.content['roi_builder']['args']
        roi_builder_kwargs = self._config.content['roi_builder']['kwargs']
        roi_builder = roi_builder_class(
            *roi_builder_args,
            **roi_builder_kwargs
        )

        # Initialize drawer
        drawer_class = self._pick_class("drawer")
        drawer_args = self._config.content['drawer']['args']
        drawer_kwargs = self._config.content['drawer']['kwargs']

        drawer_kwargs["video_out_fps"] = (
            # if a video_out_fps is available in the drawer config, take it
            drawer_kwargs["video_out_fps"] or
            # otherwise the one specified by the user
            self._user_data["framerate"] or
            # if the user specified nothing, match to the camera
            self._config.content['io']['camera']['kwargs']['framerate']
        )

        drawer = drawer_class(
            *drawer_args,
            video_out=self.video_out,
            **drawer_kwargs
        )

        # Pick tracker class and initialize recognizer
        tracker_class = self._pick_class("tracker")
        self.recognizer = Recognizer(
            tracker_class, camera_class, roi_builder, self.result_writer, drawer,
            user_data=self._user_data,
            adaptation_offset=self.adaptation_offset,
        )

        self._settings.update(self.recognizer.settings)

    def initialise_submodules(self):

        logger.debug("Starting submodules")
        logger.debug(self._submodules)

        self.initialise_result_writer()

        if self.control:
            self.initialise_controller()

        if self.recognize:
            self.initialise_recognizer()

        logger.debug(self._submodules)


    @property
    def last_drawn_frame(self):
        if self.recognize:
            return self.recognizer.drawer.last_drawn_frame
        else:
            return None

    @property
    def last_t(self):
        if self.recognize:
            return self.recognizer.last_t
        else:
            None

    @property
    def clock(self):

        clock = None
        if self.control:
            if self.controller is not None:

                adaptation_time = "%s / %s" % tuple([iso_format(hours_minutes_seconds(e)) for e in [self.controller.adaptation_left, self.controller._adaptation_offset]])

                if self.controller.running:
                    experiment_time = "%s / %s" % tuple([iso_format(hours_minutes_seconds(e)) for e in [self.controller.elapsed_seconds, self.controller.programmer.duration]])
                else:
                    experiment_time = None


                clock = {
                    "adaptation_time": adaptation_time,
                    "experiment_time": experiment_time
                }

        return clock


    def run(self):
        r"""
        Start all the submodules.
        """
        super().run()
        self.initialise_submodules()

        while not self.stopped and self.elapsed_seconds < self._max_duration:

            # TODO check next frame has come!
            # self.recognizer.load_camera()
            # # prepare recognizer upon user input
            # self.recognizer.prepare()
            # # start recognizer upon user input
            # self.recognizer.start()
            self._end_event.wait(1/self.sampling_rate)
            if self.control:

                if self.controller is not None:
                    self.controller.last_t = self.last_t
                    for thread in self.controller.programmer.paradigm:
                        if thread.is_alive():
                            thread.tick(self.last_t)



                if self.controller.progress > 100:
                    self.stop_experiment()
                    break

        return

    def stop(self):
        """
        Stop everything!
        """
        super().stop()
        self.stop_experiment(force=True)

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

            # start tracking animals
            self.recognizer.start()

        if self.control:
            # start the paradigm loaded in the controller
            self.controller.start()


        self.result_writer.initialise_metadata(self.metadata)
        self.result_writer.initialise_roi_map(self.recognizer.rois)



    def stop_experiment(self, force=False):
        """
        Convenience combination of commands targeted to stop an experiment.

        * The recognizer stops tracking and recording frames
        * The controller stops doing experiments
        * The result writer clears its cache

        NOTE: This does not stop the execution of ControlThread.run().
        Only the stop() method can do that.
        """

        if not self._user_data["wrap"] or force:

            if self.recognize:
                self.recognizer.stop()

            if self.control:
                self.controller.stop()

            self.result_writer.clear()
