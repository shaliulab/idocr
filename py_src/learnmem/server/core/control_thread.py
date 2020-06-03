# Standard library imports
import datetime
import logging
# import shutil

# Local application imports
from learnmem.server.controllers.controllers import Controller
from learnmem.server.core.base import Base, Root
from learnmem.server.trackers.simple_tracker import SimpleTracker
from learnmem.server.trackers.adaptive_bg_tracker import AdaptiveBGModel
from learnmem.server.io.saver import SimpleSaver
from learnmem.configuration import LearnMemConfiguration
from learnmem.helpers import get_machine_id, get_machine_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ControlThread(Base, Root):
    r"""
    A class to orchestrate the communication between the server
    and all the IDOC modules
    """

    _option_dict = {

        'tracker': {
            'possible_classes': [
                #DefaultTracker,
                SimpleTracker, AdaptiveBGModel
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

    _odor_a = "A" #overriden by conf and user
    _odor_b = "B" #overriden by conf and user
    _columns = ["t"]
    sampling_rate = 50 # overriden by conf


    def __init__(self, machine_id, version, result_dir, experiment_data, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._settings = {"adaptation_time": 0}
        self._submodules = {}


        self.machine_id = machine_id
        self.version = version
        self._result_dir = result_dir

        # TODO: Fix this dirty init function
        config = LearnMemConfiguration()
        for k in config.content['experiment']:
            setattr(self, k, config.content['experiment'][k])

        ## Assignment of attributes
        self.control = experiment_data['control']
        self.track = experiment_data['track']
        self.save = experiment_data['save']

        # self.reporting = experiment_data["reporting"]
        self.camera = experiment_data["camera"]
        self.video_path = experiment_data["video_path"]

        self.mapping_path = experiment_data["mapping_path"] or config.content['controller']['mapping_path']  # pylint: disable=line-too-long
        self.program_path = experiment_data["program_path"]
        self.output_path = experiment_data["output_path"]
        self.arduino_port = experiment_data["arduino_port"]
        self.board_name = experiment_data["board_name"] or config.content['controller']['board_name'] # pylint: disable=line-too-long
        self.experimenter = experiment_data["experimenter"]
        self._status = {}

        logger.info("Start time: %s", datetime.datetime.now().isoformat())


    @property
    def info(self):
        return self._info

    @info.getter
    def info(self):

        config = LearnMemConfiguration()
        logging.debug('Control thread is updating the info')
        status = 'offline'

        if self.track:
            self._info["tracker"] = self.tracker.info
            status = 'running'
        else:
            self._info["tracker"] = {"status": "offline"}

        if self.control:
            self._info["controller"] = self.controller.info
            status = 'running'

        else:
            self._info["controller"] = {"status": "offline"}

        self._info.update({
            "id": get_machine_id(),
            "location": config.content["experiment"]["location"],
            "name": get_machine_name(),
            "status": status

        })
        logging.debug('ControlThread.info OK')
        return self._info

    @property
    def adaptation_time(self):
        return self._settings['adaptation_time']

    def logs(self):
        return {"logs": []}

    @property
    def controlling(self):
        if self.controller is not None:
            return self.controller.status == 'running'
        return False

    @property
    def tracking(self):
        if self.tracker is not None:
            return self.tracker.status == 'running'
        return False

    @property
    def status(self):
        return self._status

    @status.getter
    def status(self):
        r"""
        """

        self._status.update({
            "tracker": self.tracking,
            "controller": self.controlling,
        })


        if not self.running:
            self._status["control_thread"] = "idle"
            return self._status

        if self.ready and not self.running:
            self._status["control_thread"] = 'ready'
            return self._status

        if self.running and not self.stopped:
            self._status["control_thread"] = "running"
            return self._status

        if self.stopped:
            self._status["control_thread"] = "stopped"
            return self._status

        else:
            logger.warning('%s status undefined', self.__class__.__name__)
            self._status["control_thread"] = 'undefined'
            return self._status

    def stop(self):
        r"""
        Respond to user input by stopping all dependent modules.
        and setting your status to stopped.
        """

        super().stop()
        if self.track:
            self.tracker.stop()

        if self.controller:
            self.controller.stop()

        self.saver.stop()

        # answer = 'Y'

        # if answer == 'N':
        #     try:
        #         logger.info('Removing files')
        #         shutil.rmtree(self.saver.output_dir)
        #     # in case the output_dir is not declared yet
        #     # because we are closing early
        #     except TypeError:
        #         pass
        # elif answer == 'Y':
        #     logger.info('Keeping files')
        #     # self.saver.copy_logs(self.config)

        # else:
        #     pass

        # TODO Come up with a more elegant solution than this
        # https://stackoverflow.com/questions/4541190/how-to-close-a-thread-from-within
        # sys.exit(0)
        return


    def load_program(self, program_path):
        self.controller.load_program(program_path)

    def list_programs(self):
        # TODO remove me
        logger.info("Running controller.list()")
        return self.controller.list()

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
    def tracker(self):
        if self.track:
            return self._submodules["tracker"]

    @tracker.setter
    def tracker(self, tracker):
        self._submodules["tracker"] = tracker
        self._settings.update(tracker.settings)

    @property
    def controller(self):
        if self.control:
            return self._submodules["controller"]

    @controller.setter
    def controller(self, controller):
        self._submodules["controller"] = controller
        self._settings.update(controller.settings)

    @property
    def saver(self):
        return self._submodules["saver"]

    @saver.setter
    def saver(self, saver):
        self._submodules["saver"] = saver


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
            logging.info("Action %s is not valid. Please select one in [run, stop ready].", action)


        return self.status

    def run(self):
        r"""
        Initialize a controller
        """
        super().run()

        if self.control:
            logger.info('Initializing controller board')
            controller = Controller(
                mapping_path=self.mapping_path,
                program_path=self.program_path,
                board_name=self.board_name,
                arduino_port=self.arduino_port
            )
            self._settings.update(controller.settings)

            self._columns.extend(controller.columns)
            self.controller = controller

        if self.track:
            logger.info('Initializing tracker')
            print(self.camera)
            tracker = self._option_dict['tracker']['default_class'](
                camera_name=self.camera,
                video_path=self.video_path
            )

            tracker.load_camera()
            tracker.init_image_arrays()

            self._columns.extend(tracker.columns)
            self.tracker = tracker

        self.saver = self._option_dict['saver']['default_class'](
            control=self.control, # TODO Remove dependency
            track=self.track, # Remove dependency
            result_dir=self._result_dir
        )
        self.saver.set_columns(self._columns)

        while not self.stopped:

            # if self.control and self.save:
            #     if self.controller.running:
            #         # TODO update pin_state
            #         self.saver.push_controller_data(data)

            #         if self.controller.stopped:
            #             self.saver.stop()
            #             break

            # if self.track and self.save:
            #     for row in self.tracker.row_all_flies.values():
            #         row.update(self.data)
            #         self.saver.save_video(
            #             self.tracker.frame_original,
            #             self.tracker.frame_color
            #         )

            # TODO check next frame has come!
            self._end_event.wait(1/self.sampling_rate)


        return