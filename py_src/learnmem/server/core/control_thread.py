# Standard library imports
import datetime
import logging
import time
import shutil
from threading import Thread, Event
import traceback

# Local application imports
from learnmem.server.controllers.controllers import Controller
from learnmem.orevent import OrEvent
from learnmem.server.trackers.trackers import SimpleTracker
from learnmem.server.io.saver import SimpleSaver
from learnmem.configuration import LearnMemConfiguration

logger = logging.getLogger(name=__name__)
logger.setLevel(logging.INFO)


class ControlThread(Thread):

    _option_dict = {

        'tracker': {
            'possible_classes': [
                #DefaultTracker,
                SimpleTracker,
                #AdaptiveBGModel
            ],
            'default_class': SimpleTracker
        },

        'saver': {
            'possible_classes': [

                SimpleSaver
            ],
            'default_class': SimpleSaver
        }
    }

    _program_path = "programs"
    _adaptation_time = 0 # overriden by conf and user
    _odor_A = "A" #overriden by conf and user
    _odor_B = "B" #overriden by conf and user
    _info = {}
    saver = None
    controller = None
    tracker = None
    _columns = ["t"]
    daemon = True
    sampling_rate = 50 # overriden by conf
    t = 0

    play_start = 0
    record_start = 0

    _events = {}
    _ui_settings = {}

    data = {"t": 0, "t0": 0}

    def __init__(self, machine_id, version, result_dir, experiment_data):

        self.machine_id = machine_id
        self.version = version
        self._result_dir = result_dir

        # TODO: Fix this dirty init function
        CFG = LearnMemConfiguration()
        for k in CFG.content['experiment']:
            setattr(self, k, CFG.content['experiment'][k])

        ## Assignment of attributes
        self.control = experiment_data['control']
        self.track = experiment_data['track']

        self.control_thread_start = datetime.datetime.now()

        self.controller_done = Event()
        self.play_event = Event()
        self.stop_event = Event()
        self.record_event = Event()
        self.arena_ok_event = Event()
        self.record_end = Event()

        self.load_program_event = Event()
        self.exit = Event()
        self.exit_or_record = OrEvent(self.exit, self.record_event)

        self.reporting = experiment_data["reporting"]
        self.camera = experiment_data["camera"]
        self.video = experiment_data["video"]

        self.mapping_path = experiment_data["mapping_path"] or CFG.content['controller']['mapping_path']
        self.program_path = experiment_data["program_path"]
        self.output_path = experiment_data["output_path"]
        self.dev_port = experiment_data["arduino_port"]


        self.board = experiment_data["board"] or CFG.content['controller']['board']

        self.timestamp_seconds = 0
        self.experimenter = experiment_data["experimenter"]

        logger.info("Start time: %s", self.control_thread_start.strftime("%Y-%m-%d-%H:%M:%S"))
        super().__init__()

    def get_events(self):

        self._events = {
            "play": self.play_event.is_set(),
            "arena_ok": self.arena_ok_event.is_set(),
            "record": self.record_event.is_set(),
            "exit": self.exit.is_set()
        }

    def get_ui_settings(self):

        self._ui_settings = {
            "program_path": self.program_path,
            "frame_color": self.frame_color
        }

    def _update_info(self):

        self.get_events()
        self.get_ui_settings()

        self._info.update(self._events)
        self._info.update(self._ui_settings)

    @property
    def info(self):
        return self._info

    @property
    def frame_color(self):

        try:
            return self.tracker.frame_color

        except AttributeError:
            return None

    def get_experiment_settings(self):
        r"""
        A method to retrieve settings that the user can change in the UI
        """

        try:
            stream = getattr(self.tracker, "stream", None)
            exposure_time = stream.get_exposure_time()
            framerate = stream.get_fps()
        except AttributeError:
            exposure_time = None
            framerate = None

        return {
            "exposure_time": exposure_time,
            "fps": framerate,
            "adaptation_time": self._adaptation_time
        }

    def play(self):
        """
        Signal the play event has been set
        Set the play_start time
        Turn on the IR light
        Initialize the camera and fetch frames for an undefinite time
        This is the callback function of a button
        """
        if self.play_event.is_set():
            return

        self.play_event.set()
        self.play_start = datetime.datetime.now()

        if self.track:
            self.tracker.toprun()

    def record(self):
        """
        Signal the record event has been set
        Set the record_start time
        Attempt to run the program in the controller program
        This is the callback function of a button
        """

        # Set the record_event so the data recording methods
        # can run (if_record_event decorator)

        if not self.controller:
            raise Exception("No controller program is loaded. Are you sure it is ok?")

        self.record_event.set()
        self.data["t0"] = time.time()
        self.record_start = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.saver.launch(self.record_start)

        try:
            logger.info("Running controller")
            self.controller.t0 = self.data["t0"]
            self.controller.start()

        except Exception as e:
            logger.warning('Could not run controller board.')
            logger.warning(e)
            logger.warning(traceback.print_exc())
            return None

        self.saver.save_odors(self._odor_A, self._odor_B)

    def close(self, answer="Y"):
        """
        Set the exit event
        This event is listened to by processes in the Tracker and the Controller
        classes. Upon setting this event, these processes stop
        """
        self.exit.set()
        if answer == 'N':
            try:
                logger.info('Removing files')
                shutil.rmtree(self.saver.output_dir)
            # in case the output_dir is not declared yet
            # because we are closing early
            except TypeError:
                pass
        elif answer == 'Y':
            logger.info('Keeping files')
            # self.saver.copy_logs(self.config)

        else:
            pass
        return True

    def ok_arena(self):
        """
        Signal the arena_ok event has been set
        This is the callback function of a button
        """
        logger.info("Pressed arena confirmation button")
        self.arena_ok_event.set()

    def update(self, param_name, value):
        if param_name in ["adaptation_time"]:
            setattr(self, param_name, value)

        elif param_name == "fps":
            try:
                self.tracker.camera.set_fps(value)
            except AttributeError as e:
                logger.warning(e)

        elif param_name == "exposure_time":
            try:
                self.tracker.camera.set_exposure_time(value)
            except AttributeError as e:
                logger.warning(e)

    def load_program(self, program_path):
        self.controller.programmer.load(program_path)

    def list_programs(self):
        return self.controller.programmer.list()

    @property
    def mapping(self):
        if self.control:
            return self.controller.mapping
        return None

    @property
    def pin_state(self):
        if self.control:
            return self.controller.pin_state

    def run(self):
        r"""
        Initialize a controller
        """

        if self.control:
            logger.info('Initializing controller board')
            self.controller = Controller(
                mapping_path=self.mapping_path,
                program_path=self.program_path,
                board=self.board,
                devport=self.dev_port
            )

            self._columns.extend(self.controller.columns)

        if self.track:
            logger.info('Initializing tracker')
            self.tracker = self._option_dict['tracker']['default_class'](control_thread=self, camera=self.camera, video=self.video)
            self.tracker.load_camera()
            self.tracker.init_image_arrays()

            self._columns.extend(self.tracker.columns)

        self.saver = self._option_dict['saver']['default_class'](control=self.control, track=self.track, result_dir=self._result_dir)
        self.saver.set_columns(self._columns)

        while True:
            self._update_info()
            self.t = round(time.time() - self.data["t0"], 5)
            self.data.update({"t": self.t})


            if self.control:
                if self.controller.start_event.is_set():
                    data = self.data.copy()
                    data.update(self.controller.pin_state)
                    # logger.warning("pin_state")
                    # logger.warning(self.controller.pin_state)
                    self.saver.process_row(data)

                    if self.controller.end_event.is_set():
                        self.saver.stop()
                        break

            if self.track:
                for row in self.tracker.row_all_flies.values():
                    row.update(self.data)
                    self.saver.process_row(row)

                self.saver.save_video(
                    self.tracker.frame_original,
                    self.tracker.frame_color
                )

            # TODO check next frame has come!
            time.sleep(1/self.sampling_rate)


