# Standard library imports
import argparse
import datetime
import logging
from pathlib import Path
import os.path
import sys
import threading
import time
import signal

# Third party imports
import cv2
import numpy as np
import yaml

# Local application imports
from arduino import LearningMemoryDevice
from lmdt_utils import setup_logging
from orevent import OrEvent
from gui_framework.desktop_app import TkinterGui
from tracker import Tracker
from LeMDT import ROOT_DIR, PROJECT_DIR

DjangoGui = None

# Set up package configurations
setup_logging()

GUIS = {'django': DjangoGui, 'tkinter': TkinterGui}

config_yaml = Path(PROJECT_DIR, "config.yaml").__str__()


# @mixedomatic
class Interface():

    def __init__(self, arduino=False, track=False,
    mapping_path=None,
    program_path=None,
    blocks=None, port=None, camera=None, video=None, reporting=False, config=config_yaml,
    duration=None, experimenter=None, gui=None):

        with open(config, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)


        ## Initialization of attributes
        # Timestamps for important events
        self.interface_start = None  # Instantation of the Interface class 
        self.arduino_start = None # Right before .start() the arduino threads
        self.tracking_start = None

        # Framework used to show graphics
        self.gui = None

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
        self.log = None
        self.statusbar = None

        ## Assignment of attributes
        self.gui = gui
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


        self.reporting = reporting
        self.camera = camera
        self.video = video

        if mapping_path is None: mapping_path = Path(PROJECT_DIR, 'mappings', 'main.csv').__str__()
        if program_path is None: program_path = Path(PROJECT_DIR, "programs", 'ir.csv').__str__()

        self.mapping_path = mapping_path
        self.program_path = program_path

        self.blocks = blocks
        self.port = port
        if gui:
            self.gui = GUIS[gui](interface=self)

        self.timestamp = 0
        self.duration = duration if duration else self.cfg["interface"]["duration"]
        self.experimenter = experimenter if experimenter else self.cfg["tracker"]["experimenter"]
        self.log = logging.getLogger(__name__)
        
        self.log.info("Start time: {}".format(self.interface_start.strftime("%Y%m%d-%H%M%S")))
        self.interface_initialized = False
        self.log.info('Interface initialized')


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
        print(self.camera)
        print(self.video)
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
            interface=self,
            mapping_path=self.mapping_path,
            program_path=self.program_path,
        )
        device.connect_arduino_board(self.port)
        device.prepare('exit')
        self.device = device
    
    def close(self, signo=None, _frame=None):
        """
        Set the exit event
        This event is listened to by processes in the Tracker and the LearningMemoryDevice
        classes. Upon setting this event, these processes stop
        """
        self.exit.set()
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
        
        if self.arduino:
            self.device.toprun(self.device.threads["exit"])

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

    
    def init_components(self):
        
        self.init_control_c_handler()
        if self.arduino:
            self.init_device()
    
        if self.track:
            self.init_tracker()

        self.gui.create()


    
    def start(self):
        """
        Launch the tkinter GUI and update it accordingly
        as long as there is a GUI selected
        and the exit event has not been set
        """

        self.init_components()
        while not self.exit.is_set() and self.gui is not None:
            # print(type(self.device.mapping))
            self.gui.run()
