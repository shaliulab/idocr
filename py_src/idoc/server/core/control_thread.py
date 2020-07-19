# Standard library imports
import datetime
import logging
import os.path
import time
import traceback

import pandas as pd

# Local application imports
from idoc.server.controllers.controllers import Controller
from idoc.server.core.base import Base, Root, Status
from idoc.server.core.recognizer import Recognizer
# from idoc.server.trackers.simple_tracker import SimpleTracker
from idoc.server.trackers.adaptive_bg_tracker import AdaptiveBGModel
from idoc.server.io.result_writer import CSVResultWriter
from idoc.configuration import IDOCConfiguration
from idoc.helpers import get_machine_id, get_machine_name
from idoc.server.io.pylon_camera import PylonCamera
from idoc.server.io.opencv_camera import OpenCVCamera
from idoc.server.roi_builders.roi_builders import DefaultROIBuilder
from idoc.server.roi_builders.high_contrast_roi_builder import HighContrastROIBuilder
from idoc.server.controllers.boards import ArduinoDummy, ArduinoMegaBoard, ArduinoBoard
from idoc.server.roi_builders.target_roi_builder import IDOCROIBuilder
from idoc.server.drawers.drawers import DefaultDrawer
from idoc.debug import IDOCException
from idoc.helpers import hours_minutes_seconds, iso_format, MachineDatetime

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


    valid_actions = ["start", "stop", "warm_up", "start_experiment", "stop_experiment", "reset_experiment"]

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
        self._max_duration = user_data['max_duration'] or self._config.content['experiment']['max_duration']

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
        self.description = ""

        logger.info("Control thread initialized")
        self.initialise_submodules()
        logger.info("Control thread submodules initialized")

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

    @adaptation_time.setter
    def adaptation_time(self, adaptation_time):
        self._settings['adaptation_time'] = adaptation_time * 60

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
            {"field": "user_data", "value": self._user_data},
            {"field": "description", "value": self.description}
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

        self._info["result_writer"] = self.result_writer.info

        self._info.update({
            "id": self.machine_id,
            "location": self._location,
            "name": self.machine_name,
            "status": self.status["control_thread"],
            "clock": self.clock,
            "settings": self.settings,
            "result_writer": {"status": self.result_writer.status}

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
        self._settings['recognizer'] = recognizer.settings


    @property
    def controller(self):
        if self.control:
            return self._submodules["controller"]

    @controller.setter
    def controller(self, controller):
        self._submodules["controller"] = controller
        self._settings['controller'] = controller.settings

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
                logger.info("Running action %s on module %s", action, instance)
                getattr(instance, action)()

        except RuntimeError as error:
            logger.warning("You passed action: %s. %s is already started", action, submodule)

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
            *result_writer_args,
            **result_writer_kwargs
        )

        if self._user_data['start_datetime'] is not None:
            self.result_writer.start_datetime = self._user_data['start_datetime']


    def initialise_controller(self):
        logger.debug('Starting controller')

        self.controller = Controller(
            mapping_path=self._user_data["mapping_path"],
            paradigm_path=self._user_data["paradigm_path"],
            result_writer=self.result_writer,
            board_class=self._pick_class("board"),
            arduino_port=self._user_data["arduino_port"],
            use_wall_clock=self._user_data["use_wall_clock"]
        )
        # self.controller.experiment_start = self.experiment_start
        self._settings['controller'] = self.controller.settings


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

        drawer_kwargs["framerate"] = (
            # if a video_out_fps is available in the drawer config, take it
            drawer_kwargs["framerate"] or
            # otherwise the one specified by the user
            self._user_data["framerate"] or
            # if the user specified nothing, match to the camera
            self._config.content['io']['camera']['kwargs']['framerate']
        )

        if self._user_data['start_datetime'] is not None:
            start_datetime = self._user_data['start_datetime']
            drawer_kwargs['video_out'] = os.path.join(self._result_dir, self.machine_id, self.machine_name, start_datetime, '%s_%s.avi' % (start_datetime, self.machine_id))

        drawer = drawer_class(
            *drawer_args,
            **drawer_kwargs
        )

        # Pick tracker class and initialize recognizer
        tracker_class = self._pick_class("tracker")
        recognizer = Recognizer(
            tracker_class, camera_class, roi_builder, self.result_writer, drawer,
            user_data=self._user_data
        )
        self._add_submodule("recognizer", recognizer)

    def initialise_submodules(self):

        self.initialise_result_writer()

        if self.control:
            self.initialise_controller()

        if self.recognize:
            self.initialise_recognizer()

    @property
    def last_drawn_frame(self):
        if self.recognize:
            return self.recognizer.drawer.last_drawn_frame
        else:
            return None

    @property
    def last_t(self):
        if self.recognize and self.running:
            return self.recognizer.last_t

        return 0

    @property
    def clock(self):

        experiment_time = None
        adaptation_time = None

        if self.control:
            if self.controller is not None:

                adaptation_time = "%s / %s" % tuple([iso_format(hours_minutes_seconds(e)) for e in [
                    self.controller.adaptation_left,
                    self.controller.adaptation_offset
                ]])

            if self.controller.running:
                experiment_time = "%s / %s" % tuple([iso_format(hours_minutes_seconds(e)) for e in [
                    self.controller.elapsed_seconds,
                    self.controller.duration
                ]])


        clock = {
            "adaptation_time": adaptation_time,
            "experiment_time": experiment_time
        }

        return clock


    def run(self):
        """
        Update the submodules if required as long as the experiment can go on:
        * The elapsed seconds since this function was called is less than max_duration
        * Controller progress is les than 100%
        * The stop experiment method is not called

        If any of the three statements above stop are not True, the function terminates execution
        """
        super().run()

        # if self.recognize:
        #     self.recognizer.start_datetime = self.start_datetime
        #     self.recognizer.drawer.video_out = self.video_out

        if self.control:
            self.controller.adaptation_offset = self.adaptation_offset

        while not self.stopped and self.elapsed_seconds < self._max_duration:

            self._end_event.wait(1/self.sampling_rate)

            if self.control and self.controller is not None:
                self.controller.tick(self.last_t)
                if self.controller.progress > 100:
                    logger.info("Progress reached 100%")
                    self.stop_experiment()
                    break

        if self._user_data['run']:
            self.stop()

        return

    def stop(self):
        """
        Stop everything!
        """
        super().stop()
        self.stop_experiment(force=True)
        logger.info('Quitting control thread')


    def warm_up(self):
        """
        Convenience method to start the recognizer
        with the minimal controller hardware required to do an experiment
        This is listed in the _always_on_hardware list of the controller.
        """

        self.controller.run_minimal()
        self.recognizer.prepare()
        self.recognizer.start()


    def start_experiment(self):
        """
        Convenience combination of commands targeted to start an experiment:

        * The start datetime of the experiment is set
        * The recognizer starts if it is not already
          (by) means of another method with the power of starting the recognizer
        * The controller starts executing its paradigm
        * The METADATA and ROI_MAP tables are generated
        """

        # set the self.start_datetime property to now with format
        # %YYYYY-MM-DD_HH-MM-SS
        self._set_start_datetime()

        if self._user_data['start_datetime'] is not None:
            self.result_writer.start_datetime = self._user_data['start_datetime']
        else:
            self.result_writer.start_datetime = self.start_datetime

        # allow the result_writer to write to disk the incoming data from now on
        self.result_writer.set_running()

        logger.warning("Saving results to %s", self.result_writer.result_dir)

        if self.recognize:
            self.recognizer.drawer.video_out = os.path.join(self._result_dir, self.machine_id, self.machine_name, self.start_datetime, self.run_id + '.avi')
            self.recognizer._time_running = True

            if not self.recognizer.ready:
                try:
                    # if the recognizer is not ready, it needs to prepare:
                    # * find the regions of interest (ROIS)
                    # * bind a tracker to each ROI

                    if self.controller is not None:
                        self.controller.run_minimal()

                    self.recognizer.prepare()
                except Exception as error:
                    logger.warning("Could not prepare recognizer. Please try again")
                    logger.warning(error)
                    logger.warning(traceback.print_exc())
                    return None

            if not self.recognizer.running:
                # start tracking animals
                self.recognizer.start()

        if self.control:
            # start the paradigm loaded in the controller
            self.controller.start()


        self.result_writer.initialise_metadata(self.metadata)
        if self.recognize and self.recognizer is not None:
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
                if not self.recognizer.stopped:
                    self.recognizer.stop()

            if self.control:
                if not self.controller.stopped:
                    self.controller.stop()

            self.result_writer.clear()


    def reset_experiment(self):
        self.stop_experiment(force=True)
        Status.run(self)
        self.initialise_submodules()
