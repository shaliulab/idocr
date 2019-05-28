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
from saver import Saver
from tkinter_gui import TkinterGui
from tracker import Tracker

DjangoGui = None

# Set up package configurations
setup_logging()
from LMDT import ROOT_DIR

guis = {'django': DjangoGui, 'tkinter': TkinterGui}


# @mixedomatic
class Interface():

    def __init__(self, arduino=False, track=False, mapping = None, program = None, blocks = None, port = None,
                 camera = None, video = None, reporting=False, config = "config.yaml",
                 duration = None, experimenter = None, gui = "tkinter", ir = True
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


        # Tracker and Device objects
        self.tracker = None
        self.device = None


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
        self.init_time = datetime.datetime.now()

        self.arduino_done = True
        self.arduino_stopped = True
        
        self.stop = False
        self.play_event = threading.Event()
        self.stop_event = threading.Event()
        self.record_event = threading.Event()
        self.arena_ok_event = threading.Event()
        self.load_program_event = threading.Event()

        self.exit = threading.Event()

        self.exit_or_record = OrEvent(self.exit, self.record_event)

        self.play_start = None
        self.record_start = None
        self.ir = ir

        

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
        self.mapping_path = Path(ROOT_DIR, 'mappings', 'main.csv').__str__() if mapping is None else mapping
        self.program_path = program
        self.ir_path = Path(ROOT_DIR, "programs", 'ir.csv')

        self.blocks = blocks
        self.port = port
        self.gui = guis[gui](interface = self)

        self.timestamp = 0
        self.duration = duration if duration else self.cfg["interface"]["duration"]
        self.experimenter = experimenter if experimenter else self.cfg["tracker"]["experimenter"]
        self.log = logging.getLogger(__name__)
        
        self.log.info("Start time: {}".format(self.init_time.strftime("%Y%m%d-%H%M%S")))
        self.interface_initialized = False
        self.log.info('Interface has been initialized')
    
   
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

    def load_tracker(self):
        """
        Initialize the camera tracking and the arduino controls
        """

        # Setup camera tracking
        ###########################
        if self.track:
            self.log.info("Initializing tracker")
            tracker = Tracker(interface=self, camera=self.camera, video=self.video)
        else:
            tracker = None
        self.tracker = tracker

    def load_device(self, stop_event_name='exit'):

        program_path = self.ir_path if self.program_path is None else self.program_path

        self.device = LearningMemoryDevice(
            interface=self,
            mapping_path=self.mapping_path,
            program_path=program_path,
            port=self.port
        )

        self.prepare_device(stop_event_name)
        if self.ir:
            self.device.run(threads=self.threads)
        self.log.info('Turning IR on')
        

            
    def prepare_device(self, stop_event_name):

    # Setup Arduino controls
    ##########################
        # initialize board
        if self.ir and not self.load_program_event.is_set():
            self.log.info("Initializing Arduino board controls")
        if self.load_program_event.is_set():
            print('Reloading program')
            self.log.debug('Reloading program')
            self.device.load_program(program_path = self.program_path, reload=True)

        # power off any pins if any
        self.device.power_off_arduino(exit=False, log=False)
        # prepare the arduino parallel threads
        self.device.prepare(stop_event_name=stop_event_name)

        
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
        self.play_start = datetime.datetime.now()
        if self.ir:
            self.load_device('exit_or_record')

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
        
        self.record_event.set()
        self.record_start = datetime.datetime.now()
        self.log.info("Starting recording. Savers will cache data and save it to csv files")

        if not self.arduino:
            self.log.warning("No arduino program is loaded. Are you sure it is ok?")
            self.control_c_handler()
            # set the event so the savers actually save the data and not just ignore it
            
        else:
            # if self.interface_initialized:
            #     return None            
            try:
                self.log.info("Running Arduino")
                self.device.run(threads=self.threads)
            except Exception as e:
                self.log.exception('Could not run Arduino board. Check exception')
                self.log.exception(e)

    
    def ok_arena(self):
        self.log.info("Fixing arena contours and stopping further detection")
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
