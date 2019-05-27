# Standard library imports
import argparse
import datetime
import logging
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
from lmdt_utils import setup_logging
from saver import Saver
from tracker import Tracker
from arduino import LearningMemoryDevice
from tkinter_gui import TkinterGui

DjangoGui = None

# Set up package configurations
setup_logging()
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

guis = {'django': DjangoGui, 'tkinter': TkinterGui}


# @mixedomatic
class Interface():

    def __init__(self, arduino=False, track=False, mapping = None, program = None, blocks = None, port = None,
                 camera = None, video = None, reporting=False, config = "config.yaml",
                 duration = None, experimenter = None, gui = "tkinter"
                 ):

        with open(config, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile,  Loader=yaml.FullLoader)


        ## Initialization of attributes
        # Timestamps for important events
        self.init_time = None  # Instantation of the Interface class 
        self.arduino_start = None # Right before .start() the arduino threads
        self.tracking_start = None

        # Framework used to show graphics
        self.gui = None

        # Boolean flags indicating if arduino and or track are active
        self.arduino = None
        self.track = None
        self.tracker = None

        self.arduino_done = None    # becomes true if all events are complete
        self.arduino_stopped = None # becomes true if user stops the arduino controls prematurily with Control C       
        self.exit = None            # later assigned a threading.Event()
        self.stream_finished = None # becomes true if stream is finished (i.e more frames are not available)
        self.camera_closed = None   # becomes true if user stops tracking with X/q

        self.metadata_saver = None
        self.data_saver = None
        self.threads = None
        self.threads_finished = None
        
        self.gray_color = None
        self.frame_color = None
        self.gray_gui = None
        self.stacked_arenas = None

        self.reporting = None
        self.camera = None
        self.video = None

        self.mapping_path = None
        self.filtered_mappings = None
        self.program_path = None

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
        self.init_time = datetime.datetime.now()

        self.arduino_done = True
        self.arduino_stopped = True
        self.exit = threading.Event()
        
        self.stop = False
        self.play_event = threading.Event()
        self.stop_event = threading.Event()
        self.record_event = threading.Event()
        self.arena_ok_event = threading.Event()

        self.data_saver = Saver(
            store=self.cfg["tracker"]["store"], init_time=self.init_time,
            name="data_saver", record_event=self.record_event
            )
        self.metadata_saver = Saver(
            store=self.cfg["arduino"]["store"], init_time=self.init_time,
            name="metadata_saver", record_event=self.record_event
            )

        self.threads = {}
        self.threads_finished = {}

        self.reporting = reporting
        self.camera = camera
        self.video = video
        self.mapping_path = mapping
        self.program_path = program
        self.blocks = blocks
        self.port = port
        self.gui = guis[gui](interface = self)

        self.timestamp = 0
        self.duration = duration if duration else self.cfg["interface"]["duration"]
        self.experimenter = experimenter if experimenter else self.cfg["tracker"]["experimenter"]
        self.log = logging.getLogger(__name__)
        
        self.log.info("Start time: {}".format(self.init_time.strftime("%Y%m%d-%H%M%S")))


        self.interface_initialized = False
    
   
    def cv2_update(self):
        pack = False
        if self.track:
            pack = True
            cv2.imshow("frame_color", self.frame_color)
            #cv2.imshow('transform', self.transform)
            cv2.imshow("gray_gui", self.gray_gui)
            pack = True
        
        if self.arduino:
            pass
        
        if self.track or self.arduino and pack:
            # Check if user forces leave (press q)
            q_pressed = cv2.waitKey(1) & 0xFF in [27, ord('q')]
            if q_pressed:
                self.onClose()


    
    def onClose(self, signo=None, _frame=None):
        """
        Setting the Threading.Event() (to True) triggers the controlled shutdown of 
        Arduino communication and storage of remaining cache
        """
        self.exit.set()
        if signo is not None: self.log.info("Received {}".format(signo))

        # if self.gui == "tkinter":
        #     # set the stop event, cleanup the camera, and allow the rest of
        #     # the quit process to continue
        #     self.root.quit()
            #self.root.destroy()

        # else:
            # cv2.destroyAllWindows()

    def prepare(self):
        """
        Initialize the camera tracking and the arduino controls
        """

        # Setup camera tracking
        ###########################
        if self.track:
            tracker = Tracker(interface=self, camera=self.camera, video=self.video)
        else:
            tracker = None
        self.tracker = tracker

        # Setup Arduino controls
        ##########################
        if self.arduino:
            # initialize board
            device = LearningMemoryDevice(interface=self, mapping=self.mapping_path, program=self.program_path, port=self.port)
            # power off any pins if any
            device.power_off_arduino(exit=False)
            # prepare the arduino parallel threads
            device.prepare()
        else:
            device = None
        self.device = device

    def control_c_handler(self):
        """
        Make the main thread run quit when signaled to stop
        This will stop all the threads in a controlled fashion,
        which means all the pins are turned of before the thread
        peacefully dies
        """

        signals = ('TERM', 'HUP', 'INT')
        for sig in signals:
            signal.signal(getattr(signal, 'SIG' + sig), self.onClose)

    def play(self):
        """
        Initialize arduino and camera. Run frames for an undefinite time.
        Turn on and off Arduino pins. This way, the user can test the device
        prior to any experiment 
        """
        self.play_event.set()

        if self.track:
            try:
                self.log.info("Running tracker")
                self.tracker.run()
            except Exception as e:
                self.log.exception('Could not run tracker')
                self.log.exception(e)

        
        self.interface_initialized = True

        if not self.track and not self.gui and self.arduino:
            self.log.debug("Sleeping for the duration of the experiment. This makes sense if we are checking Arduino")
            self.exit.wait(self.duration)

        
        
    def record(self):
        """
        Start recording image data and runs arduino paradigm if any
        """

        if not self.arduino:
            self.log.warning("No arduino program is loaded. Are you sure it is ok?")
            self.control_c_handler()
            # set the event so the savers actually save the data and not just ignore it
            self.record_event.set()
            self.log.info("Starting recording. Savers will cache data and save it to csv files")
            
        else:
            print(self.device.program)
            ok = input("Is the program OK? (y/n):")
            if ok == "y":
            # if self.interface_initialized:
            #     return None            
                try:
                    self.log.info("Running Arduino")
                    self.device.run(threads=self.threads)
                except Exception as e:
                    self.log.exception('Could not run Arduino board')
                    self.log.exception(e)

    
    def ok_arena(self):
        self.log.info("Stopping detection of arenas")
        self.arena_ok_event.set()
    
    def stop(self):
        self.stop = True
        self.play_event = threading.Event()
        self.stop_event.set()

    
    def start(self):
        """
        Launch the tkinter gui and update it accordingly
        """        
        while not self.exit.is_set() and self.gui is not None:
            
            # print(type(self.device.mapping))
            self.gui.update()
