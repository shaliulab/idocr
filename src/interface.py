# Standard library imports
import argparse
import datetime
import logging
import os.path
import sys
import threading
import time
import tkinter as tk
import signal

# Third party imports
import coloredlogs
import cv2
import imutils
import numpy as np
from PIL import ImageTk, Image
import yaml

# Local application imports
from frets_utils import setup_logging
from saver import Saver
from tracker import Tracker
from arduino import LearningMemoryDevice

# Set up package configurations
setup_logging()
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

# https://stackoverflow.com/questions/17985216/draw-circle-in-tkinter-python


class ResizingCanvas(tk.Canvas):
    def __init__(self,parent,**kwargs):
        tk.Canvas.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width)/self.width
        hscale = float(event.height)/self.height
        self.width = event.width
        self.height = event.height
        # resize the canvas 
        self.config(width=self.width, height=self.height)
        # rescale all the objects tagged with the "all" tag
        # self.scale("all",0,0,wscale,hscale)

    def create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)


class TkinterGui(ResizingCanvas):

    def __init__(self):

        self.gui_width = None
        self.gui_pad = None
        self.log = None
        self.tkinter_init = None
        self.canvas = None
      
        root = tk.Tk()
        # set initial size of window (800x800 and 500 pixels up)
        root.geometry("800x800+0-500")
        
        # frame = tk.Frame(root)
        # frame.pack(fill=tk.BOTH, expand=tk.YES)
        
        
        canvas = ResizingCanvas(root, width=800, height=800, highlightthickness=0, bd=0, relief='ridge')
        canvas.pack(fill=tk.BOTH, expand=tk.YES, anchor = tk.NW)
        canvas.bind("<Button-1>", self.callback)




        


        # canvas.grid()
        self.root = root
        # self.frame = frame
        self.canvas = canvas

        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_width = 250
        self.gui_pad = 20
        self.tkinter_init = True
        self.video_height = None
        self.video_width = None
        
        # staff shown in the gui
        self.frame_color = None
        self.gray_gui = None



        self.log = logging.getLogger(__name__)

    def callback(self, event):
        print("clicked at", event.x, event.y)


    # def tkinter_initialize(self):
    #     # self.stopEvent = None
        
    #     w = self.gui_width * 3 + self.gui_pad * 6
    #     # self.log.info("GUI Window size is set to {}x800".format(w))
    #     # self.root.geometry("{}x800".format(w))


    #     # tk.Frame.__init__(self, self.root)

    #     
    #     #print(self.panel.shape)
    #     #print(self.panel[0,0])
    #     # self.pack(fill=tk.BOTH, expand=1))

    def tkinter_preprocess(self, img, gui_width, gui_height=None):
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=gui_width, height=gui_height)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image

    


# @mixedomatic
class Interface(TkinterGui):

    def __init__(self, arduino=False, track=False, mapping = None, program = None, blocks = None, port = None,
                 camera = None, video = None, reporting=False, config = "config.yaml",
                 duration = None, experimenter = None, gui = "tkinter"
                 ):

        with open(config, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile)

        TkinterGui.__init__(self)

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

        self.timestamp = 0
        self.duration = duration if duration else self.cfg["interface"]["duration"]
        self.experimenter = experimenter if experimenter else self.cfg["tracker"]["experimenter"]


        statusbar = tk.Label(self.root, text="Welcome to FReTs", relief=tk.SUNKEN, anchor=tk.W)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar = statusbar


        if self.gui == "tkinter":
            self.panel = {}

        #     self.log.info("Initializing tkinter GUI")
        #     self.tkinter_initialize()
        
        self.log.info("Start time: {}".format(self.init_time.strftime("%H%M%S-%d%m%Y")))


    def tkinter_update_widget(self, img, name = "", gui_width = None, preprocess=True):

        if gui_width is None:
            gui_width = self.gui_width

        if preprocess:
            image = self.tkinter_preprocess(img, gui_width)

        if self.tkinter_init:
            label = tk.Label(self.canvas, image=image)
            label.pack(side=tk.LEFT, anchor=tk.N)
            # label.grid(
            #     row=row, column=column,
            #     padx = self.gui_pad, pady = self.gui_pad, sticky="N")
            self.panel[name] = label
            # label.image = image
            # label.pack()
            # label.place(x = x, y = y)
        else:
            self.panel[name].configure(image=image)
            self.panel[name].image = image

    
    def tkinter_update_monitor(self, mapping):
        
        filtered_mapping = mapping
        # filtered_mapping = mapping.loc[~mapping.index.isin(['ONBOARD_LED'])]

        if self.tkinter_init:

        
            for i, pin in enumerate(filtered_mapping.itertuples()):
                
                label = tk.Label(self.canvas, text = pin.Index, fg = 'white', bg = 'black')
                y = 500 + pin.x * 50
                x = 50 + pin.y * 100
                label.place(x=x-15, y=y-30)
                self.panel[i] = label
                # circle is an integer indicating the index of the shape
                # i.e. the first cirlce returns 1, the second 2 and so forth
                circle = self.canvas.create_circle(x, y, 12, fill = "red")

        
        else:
            for i, pin in enumerate(filtered_mapping.itertuples()):
                
                state = self.device.pin_state[pin.Index]
                # print(state)
                # print(self.device.pin_state)
                # print(pin.Index)
                if type(state) is bool:
                    # print('{} is boolean'.format(state))
                    color = 'yellow' if state else 'red'
                else:
                    color = 'blue'
                self.canvas.itemconfig(i+1, fill = color)

    def tkinter_update_status(self):

        c1 = self.device.overview['start'] < self.timestamp
        c2 = self.device.overview['end'] > self.timestamp
        selected_rows = c1 & c2
        active_blocks = self.device.overview.index[selected_rows].tolist()
        main_block = active_blocks[-1]

        passed = self.timestamp - self.device.overview.loc[main_block]['start']
        left = self.device.overview.loc[main_block]['end'] - self.timestamp
        time_position = np.round(np.array([passed, left]) / 60, 3)


        text = 'Running ' + ' and '.join(active_blocks) + ' blocks'
        text += ' {}m passed, {}m left'.format(*time_position)
        self.statusbar['text'] = text



        
        # import ipdb; ipdb.set_trace()

        # [self.device.program.query('block = "{}"'.format(b)) for b in self.device.block_names]





    def tkinter_update_widgets(self):
         
        ## TODO rewrite to make less verbose
        ####################################
        self.tkinter_update_widget(img=self.frame_color, name='frame_color', gui_width=self.gui_width * 2)
        self.tkinter_update_widget(img=self.gray_gui, name='gray_gui')
        # self.tkinter_update_widget(img=self.monitor, y=self.gui_pad * 2 + * (self.gui_width + self.gui_pad), x=self.gui_pad * 2 + * (self.gui_width + self.gui_pad), preprocess=False)
        self.tkinter_update_monitor(self.device.mapping)
        self.tkinter_update_status()

        if self.tkinter_init:
            # # self.interface.tkinter_init = False
            self.root.wm_title("Learning memory stream")
            self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
            self.canvas.addtag_all("all")
            self.tkinter_init = False
        
        # if self.interface.timestamp % 1 == 0:

        self.root.update_idletasks()
        # needed to close the window with X
        self.root.update()
        time.sleep(.01)
   
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

        if self.gui == "tkinter":
            # set the stop event, cleanup the camera, and allow the rest of
            # the quit process to continue
            self.root.quit()
            #self.root.destroy()

        else:
            cv2.destroyAllWindows()

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

    def start(self):
        """
        """

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

        while not self.exit.is_set() and self.gui is not None:
            
            if self.gui == "tkinter":
                if self.device.loaded:
                    # print(type(self.device.mapping))
                    self.tkinter_update_widgets()

                
            else:
                self.cv2_update()

