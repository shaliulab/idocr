# Standard library imports
import argparse
import datetime
import logging
from pathlib import Path
import os
import os.path
import sys
import threading
import time
import shutil
import signal
import ipdb
import tempfile


# Third party imports
import cv2
import numpy as np
import yaml
import pandas as pd
pd.options.mode.chained_assignment = None

# Local application imports
from .arduino import LearningMemoryDevice
from .orevent import OrEvent
from .desktop_app import TkinterGui
from .cli_app import CLIGui

from .tracker import Tracker
from . import PROJECT_DIR

DjangoGui = None

# Set up logging configurations

GUIS = {'django': DjangoGui, 'tkinter': TkinterGui, 'cli': CLIGui}

# config_yaml = Path(PROJECT_DIR, "../config.yaml").__str__()


# @mixedomatic
class Interface():

    def __init__(self, arduino=False, track=False,
    mapping_path=None,
    program_path=None,
    blocks=None, port=None, camera=None,
    video=None, reporting=False,
    config_file=None,
    output_path=None,
    # duration=None,
    experimenter=None, gui_name=None):

        

        ## Initialization of attributes
        # Timestamps for important events

        self.config_file = None
        self.config = None

        self.setup_logging()
        self.log = self.getLogger(name=__name__)

        self.interface_start = None  # Instantation of the Interface class 
        self.arduino_start = None # Right before .start() the arduino threads
        self.tracking_start = None
        self.cfg = None

        # Framework used to show graphics
        self.gui_name = None

        # Boolean flags indicating if arduino and or track are active
        self.arduino = None
        self.track = None


        # Tracker and Device objects
        self.tracker = None
        self.device = None


        self.arduino_stopped = None # becomes true if user stops the arduino controls prematurily with Control C       
        self.exit = None            # later assigned a threading.Event()
        self.stream_finished = None # becomes true if stream is finished (i.e more frames are not available)
        self.camera_closed = None   # becomes true if user stops tracking with X/q
        self.original_frame = None    
        self.gray_color = None
        self.frame_color = None
        self.gray_gui = None
        self.stacked_arenas = None
        self.min_arena_area = None
        self.reporting = None
        self.camera = None
        self.video = None

        self.filtered_mappings = None
        self.program_path = None
        self.mapping_path = None

        self.blocks = None
        self.port = None
        
        self.timestamp = None
        self.duration = None
        self.experimenter = None
        self.statusbar = None
        
        self.odor_A = None
        self.odor_B = None
        
        ## Assignment of attributes
        self.gui_name = gui_name
        self.arduino = arduino
        self.track = track
        self.interface_start = datetime.datetime.now()
     
        self.arduino_done = threading.Event()
        self.play_event = threading.Event()
        self.stop_event = threading.Event()
        self.record_event = threading.Event()
        self.arena_ok_event = threading.Event()
        self.load_program_event = threading.Event()
        self.exit = threading.Event()
        self.exit_or_record = OrEvent(self.exit, self.record_event)

        self.play_start = None
        self.record_start = None

        self.config_file = config_file


        self.reporting = reporting
        self.camera = camera
        self.video = video

        self.mapping_path = mapping_path
        self.program_path = program_path

        self.blocks = blocks
        self.port = port
        
        self.gui = None
        if gui_name:
            self.gui = GUIS[gui_name](interface=self)
        

        self.timestamp = 0
        self.experimenter = experimenter
      
        self.log.info("Start time: {}".format(self.interface_start.strftime("%Y%m%d-%H%M%S")))
        self.interface_initialized = False
        self.log.info('Interface initialized')

        self.output_path = output_path
        self.control_panel_path = Path(PROJECT_DIR, 'arduino_panel', 'tkinter.csv').__str__()

        self.fraction_area = 1
        self.answer = "Yes"

        self.odor_A = 'A'
        self.odor_B = 'B'
        self.save_results_answer = 'Yes'




    def init_tracker(self):
        """
        Initialize a Tracker object that will provice camera controls
        Load the correct stream (Pylon, webcam camera or video)

        Called by interface.init_components() method,
        upon starting the Python software
        """

        # Setup camera tracking
        ###########################
        self.log.info("Running tracker.init_tracker")
        frame_source = np.array([self.camera, self.video])
        frame_source = frame_source[[not e is None for e in frame_source]].tolist()[0]
        
        self.log.info('Frame source set to {}'.format(frame_source))

        self.tracker = Tracker(interface=self, camera=self.camera, video=self.video)
        self.tracker.set_saver()
        self.tracker.load_camera()
        self.tracker.init_image_arrays()



    def init_device(self):
        """
        Initialize a LearningMemoryDevice object that will provide Arduino controls
        Load the mappings and a default paradigm by creating (no running) the corresponding parallel threads
        Called by interface.init_components() method,
        upon starting the Python software

        Details:
            It loads a program that turns on the IR only
            This behavior only changes when self.program_path is set,
            which can be done by pasing it via --program at runtime via the CLI
        """

        self.log.info("Running interface.init_device")
        device = LearningMemoryDevice(
            interface=self
        )
        device.connect_arduino_board(self.port)
        device.prepare('exit')
        self.device = device
        self.log.info('Arduino will be run for {}'.format(datetime.timedelta(seconds= self.duration)))
        device.get_paradigm_human_readable()


    def setup_logging(self, default_path='LeMDT/logging.yaml', default_level=logging.INFO, env_key='LOG_CFG'):
        """
        Setup logging configuration
        """
        path = default_path
        value = os.getenv(env_key, None)
        if value:
            path = value
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.safe_load(f.read())

            file_handlers = [v for v in config['handlers'].keys() if v[:5] == 'file_']
            for h in file_handlers:
                # config['handlers'][f]['filename'] = tempfile.NamedTemporaryFile(prefix=config['handlers'][f]['filename'], suffix=".log").name
                filename = os.path.join(PROJECT_DIR, 'logs', config['handlers'][h]['filename']+".log")
                if os.path.exists(filename): os.remove(filename)
                config['handlers'][h]['filename'] = filename

            logging.config.dictConfig(config)

        else:
            self.log.warning('Could not find logging config file under {}'.format(path))
            logging.basicConfig(level=default_level)
            
        
        self.logging = logging
        self.config = config 

    def getLogger(self, name):
        return self.logging.getLogger(name)

        
    def close(self, signo=None, _frame=None):
        """
        Set the exit event
        This event is listened to by processes in the Tracker and the LearningMemoryDevice
        classes. Upon setting this event, these processes stop
        """
        self.exit.set()
        answer = self.save_results_answer
        if answer == 'N':
            try:
                shutil.rmtree(self.tracker.saver.output_dir)
            # in case the output_dir is not declared yet
            # because we are closing early
            except TypeError:
                pass
        else:
            # ipdb.set_trace( )
            self.tracker.saver.copy_logs(self.config)
            


        self.log.info("Running interface.close()")
        if signo is not None: self.log.info("Received %", signo)
        
    def init_control_c_handler(self):
        """
        Make the main thread run quit when signaled to stop
        This will stop all the threads in a controlled fashion,
        which means all the pins are turned of before the thread
        peacefully dies
        """

        signals = ('TERM', 'HUP', 'INT')
        for sig in signals:
            signal.signal(getattr(signal, 'SIG' + sig), self.close)

    def play(self):
        """
        Signal the play event has been set
        Set the play_start time
        Turn on the IR light
        Initialize the camera and fetch frames for an undefinite time
        This is the callback function of a button
        """
        if self.play_event.is_set():
            return None
            
        self.play_event.set()
        self.play_start = datetime.datetime.now()
        
        if self.track:
            try:
                self.log.info("Running tracker")
                self.tracker.toprun()
            except Exception as e:
                self.log.exception('Could not run tracker')
                self.log.exception(e)

        # NEEDED?
        if not self.track and not self.gui and self.arduino:
            self.log.debug("Sleeping for the duration of the experiment. This makes sense if we are checking Arduino")
            self.exit.wait(self.duration)
        
    def record(self):
        """
        Signal the record event has been set
        Set the record_start time
        Attempt to run the program in the Arduino paradigm
        This is the callback function of a button
        """
        
        # Set the record_event so the data recording methods
        # can run (if_record_event decorator)
        self.record_event.set()

        self.record_start = datetime.datetime.now()
        self.tracker.saver.init_record_start()
        self.tracker.saver.init_output_files()
        self.tracker.saver.save_paradigm()
        self.tracker.saver.save_odors(self.odor_A, self.odor_B)
        
        self.log.info("Pressed record")
        self.log.info("Savers will cache data and save it to csv files")

        if not self.arduino:
            self.log.warning("No arduino program is loaded. Are you sure it is ok?")
            
        else:
            try:
                self.log.info("Running device.toprun")
                self.device.toprun(self.device.threads["exit"])                 
                
            except Exception as e:
                self.log.exception('Could not run Arduino board. Check exception')
                self.log.exception(e)

    
    def ok_arena(self):
        """
        Signal the arena_ok event has been set
        This is the callback function of a button
        """
        self.log.info("Pressed arena confirmation button")
        self.arena_ok_event.set()

    
    def prepare_paths(self):

        if self.mapping_path is None:
            self.mapping_path = Path(PROJECT_DIR, 'mappings', 'tkinter.csv').__str__()
        else:
            self.mapping_path = Path(PROJECT_DIR, self.mapping_path).__str__()

        if self.program_path is None:
            self.program_path = Path(PROJECT_DIR, "programs", 'test.csv').__str__()
        else:
            self.program_path = Path(PROJECT_DIR, "programs", self.program_path).__str__()

   
    def load_config(self):
        
        with open(self.config_file, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

        self.prepare_paths()

        self.log.info('Mapping path:')
        self.log.info(self.mapping_path)
        self.log.info('Program path:')
        self.log.info(self.program_path)
        
        # if self.duration is None: self.duration = self.cfg["interface"]["duration"]
        if self.experimenter is None: self.experimenter = self.cfg["tracker"]["experimenter"]
        self.min_arena_area = self.cfg["arena"]["min_area"] 
        # self.control_panel_path = Path(PROJECT_DIR, 'arduino_panel', self.cfg["interface"]["filename"]).__str__()
        self.arena_width = self.cfg["arena"]["width"]
        self.arena_height = self.cfg["arena"]["height"]
       
        width = self.cfg["arena"]["width"]
        height = self.cfg["arena"]["height"]        
        empty_img = np.zeros(shape=(height*3, width*3, 3), dtype=np.uint8)
        self.stacked_arenas = [empty_img.copy() for i in range(self.cfg["arena"]["targets"])]

    
    def load_and_apply_config(self, config_file=None):
        if config_file is None:
            config_file = self.config_file
        else:
            self.config_file = config_file

        self.load_config()
        # Init zoom tab
        self.init_components()
    
        self.log.info('Config applied successfully')


    def init_components(self):
 
        self.init_control_c_handler()
        if self.arduino:
            self.log.info('Initializing Arduino board')
            self.init_device()
    
        if self.track:
            self.log.info('Initializing tracker')
            self.init_tracker()
        if self.gui_name in ['tkinter', 'django', 'cli']:
            self.gui.create()
            self.log.info('Initializing gui')

    
    def start(self):
        """
        Launch the tkinter GUI and update it accordingly
        as long as there is a GUI selected
        and the exit event has not been set
        """
        config_file = os.path.join(PROJECT_DIR, 'config.yaml')
        self.load_and_apply_config(config_file)

        while not self.exit.is_set():
            # print(type(self.device.mapping))
            self.gui.run()
            self.gui.apply_updates()
    

