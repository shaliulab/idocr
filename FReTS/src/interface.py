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
from frets_utils import setup_logging
from saver import Saver
from tracker import Tracker
from arduino import LearningMemoryDevice
from tkinter_gui import TkinterGui

DjangoGui = None

# Set up package configurations
setup_logging()
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

guis = {'django': DjangoGui, 'tkinter': TkinterGui}


# @mixedomatic
class Interface():

    def __init__(self, arduino=False, track=False, mapping = None, program = None, blocks = None, port = None,
                 camera = None, video = None, reporting=False, config = "config.yaml",
                 duration = None, experimenter = None, gui = "tkinter"
                 ):

        with open(config, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile)


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
        
        self.frame_color = None
        self.gray_gui = None

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

        self.arduino_done = True
        self.arduino_stopped = True
        self.exit = threading.Event()
        
        self.init_time = datetime.datetime.now()

        self.data_saver = Saver(store = self.cfg["tracker"]["store"], init_time = self.init_time, name = "data_saver")
        self.metadata_saver = Saver(store = self.cfg["arduino"]["store"], init_time = self.init_time, name = "metadata_saver")

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
        
        self.log.info("Start time: {}".format(self.init_time.strftime("%H%M%S-%d%m%Y")))


    
   
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
        """

        if self.track:
            tracker = Tracker(interface = self, camera = self.camera, video = self.video)
        else:
            tracker = None
        self.tracker = tracker

        # Setup Arduino controls
        ##########################
        if self.arduino:

            device = LearningMemoryDevice(interface = self, mapping = self.mapping_path, program = self.program_path, port = self.port)
            device.power_off_arduino(exit=False)
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
        print('Play')
        self.control_c_handler()

        if self.arduino:
            try:
                self.log.info("Running Arduino")
                self.device.run(threads=self.threads)
            except Exception as e:
                self.log.exception('Could not run Arduino board')
                self.log.exception(e)
        
        if self.track:
            try:
                self.log.info("Running tracker")
                self.tracker.run()
            except Exception as e:
                self.log.exception('Could not run tracker')
                self.log.exception(e)

        if not self.track and not self.gui and self.arduino:
            self.log.debug("Sleeping for the duration of the experiment. This makes sense if we are checking Arduino")
            self.exit.wait(self.duration)
    
    def start(self):
        """
        """        
        while not self.exit.is_set() and self.gui is not None:
            
            if self.device.loaded:
                # print(type(self.device.mapping))
                self.gui.update()
