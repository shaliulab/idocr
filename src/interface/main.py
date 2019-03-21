import threading
# from src.frets_utils import mixedomatic, ReadConfigMixin
from src.frets_utils import setup_logging
from src.saver.main import Saver
import tkinter as tk
Frame = tk.Frame
from PIL import ImageTk, Image
import imutils
import cv2
import datetime
import time
import yaml
import numpy as np
import logging
setup_logging()


class TkinterGui(Frame):

    def __init__(self):

        self.gui_width = None
        self.gui_pad = None
        self.log = None
        self.tkinter_init = None

        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_width = 250
        self.gui_pad = 20
        self.tkinter_init = True
        self.video_height = None
        self.video_width = None


        self.log = logging.getLogger(__name__)

    def tkinter_initialize(self):
        # self.stopEvent = None
        self.root = tk.Tk()
        w = self.gui_width * 3 + self.gui_pad * 6
        self.log.info("GUI Window size is set to {}x800".format(w))
        self.root.geometry("{}x800".format(w))
        Frame.__init__(self, self.root)

        self.panel = np.full((1,3), None)
        #print(self.panel.shape)
        #print(self.panel[0,0])
        self.pack(fill=tk.BOTH, expand=1)

        # start a thread that constantly pools the video sensor for
        # the most recently read frame
        #self.thread = threading.Thread(name="Track thread", target=self.track, args=())
        #self.thread.start()
        #self.run()

    def tkinter_preprocess(self, img, gui_width):
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=gui_width)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image

    def tkinter_update_widget(self, img, i, j, gui_width = None):

        if gui_width is None:
            gui_width = self.gui_width

        image = self.tkinter_preprocess(img, gui_width)

        if self.tkinter_init:
            print("I only run once")
            label = tk.Label(image=image)
            self.panel[i,j] = label
            self.panel[i,j].image = image
            x = self.gui_pad * (j + 1) + j * (gui_width + self.gui_pad)
            y = self.gui_pad * (i + 1) + i * (self.gui_width + self.gui_pad)
            label.place(x = x, y = y)
        else:
            self.panel[i,j].configure(image=image)
            self.panel[i,j].image = image


        



# @mixedomatic
class Interface(TkinterGui):

    def __init__(self, arduino=False, track=False, reporting=False, config = "config.yaml", duration = None, experimenter = None, gui = "tkinter"):

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
        
        self.timestamp = None
        self.duration = None
        self.experimenter = None

        ## Assignment of attributes
        self.gui = gui
        self.arduino = arduino
        self.track = track

        self.arduino_done = True
        self.arduino_stopped = True
        self.exit = threading.Event()
        
        init_time = datetime.datetime.now()

        self.metadata_saver = Saver(store = self.cfg["arduino"]["store"], init_time = init_time)
        self.data_saver = Saver(store = self.cfg["arduino"]["store"], init_time = init_time)

        self.threads = {}
        self.threads_finished = {}

        self.reporting = reporting

        self.timestamp = 0
        self.duration = duration if duration else self.cfg["interface"]["duration"]
        self.experimenter = experimenter if experimenter else self.cfg["tracker"]["experimenter"]


        if self.gui == "tkinter":
            self.log.info("Initializing tkinter GUI")
            self.tkinter_initialize()
        
        self.log.info("Start time: {}".format(init_time.strftime("%H%M%S-%d%m%Y")))

    
    def onClose(self, signo=None, _frame=None):
        # Setting the Threading.Event() (to True)
        # triggers the controlled shutdown of 
        # Arduino communication and
        # storage of remaining cache

        self.exit.set()
        if signo is not None: self.log.info("Received {}".format(signo))

        if self.gui == "tkinter":
            # set the stop event, cleanup the camera, and allow the rest of
            # the quit process to continue
            self.root.quit()
            #self.root.destroy()

        else:
            cv2.destroyAllWindows()

    def run(self):

        while not self.exit.is_set():    

            if self.gui == "tkinter":
                self.tkinter_update_widget(self.frame_color, 0, 0, gui_width = (self.gui_width + self.gui_pad) * 2)
                #self.tkinter_update('main_mask', 0, 1)
                self.tkinter_update_widget(self.gray_gui, 0, 2)
                # status = self.interface.root.after(100, self.track)
                # set a callback to handle when the window is closed
                
                self.root.update_idletasks()
                self.root.update()
                time.sleep(.01)


                if self.tkinter_init:
                    # # self.interface.tkinter_init = False
                    self.root.wm_title("Learning memory stream")
                    self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
                    self.tkinter_init = False


                
                # if self.interface.timestamp % 1 == 0:
                
            else:
                cv2.imshow("frame_color", self.frame_color)
                #cv2.imshow("mask", self.main_mask)
                #cv2.imshow('transform', self.transform)
                cv2.imshow("gray_gui", self.gray_gui)
                # Check if user forces leave (press q)
                q_pressed = cv2.waitKey(1) & 0xFF in [27, ord('q')]
                if q_pressed:
                    break

        self.onClose()



