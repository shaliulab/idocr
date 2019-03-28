# Standard library imports
import datetime
import logging
import os.path
from pathlib import Path
import sys
import time
import tkinter as tk

# Third party imports   
import cv2
import imutils
import numpy as np
from PIL import ImageTk, Image

# Local application imports
from frets_utils import setup_logging
from FReTS import ROOT_DIR, STATIC_DIR

setup_logging()

def _create_circle(self, x, y, r, **kwargs):
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle = _create_circle


class BetterButton(tk.Button):
    def __init__(self, parent, event_name, command, index, **kwargs):
        self.index = index
        photoimage = self.generate_image(event_name)
        # fname = Path(ROOT_DIR, 'static', '{}.png'.format('fly')).__str__()
        # photoimage = ImageTk.PhotoImage(file = fname)
        tk.Button.__init__(self, parent, image = photoimage, command = command, **kwargs)
        self.image = photoimage
                
    def generate_image(self, event_name):
        fname = Path(ROOT_DIR, 'static', '{}.png'.format(event_name)).__str__()
        photoimage = ImageTk.PhotoImage(file = fname)
        return photoimage

    def push(self):
        self.grid(row=0, column = self.index, padx = 10)


class TkinterGui():

    def __init__(self, interface):

        self.gui_pad = None
        self.log = None
        self.tkinter_init = None
        self.canvas = None
        self.interface = None
        self.panel = {}

        root = tk.Tk()
        # set initial size of window (800x800 and 500 pixels up)
        self.height = 800
        self.width = 800

        root.geometry("{}x{}+0-500".format(self.width, self.height))
        icon_path = Path(ROOT_DIR, STATIC_DIR, 'fly.png').__str__()
        # root.iconbitmap(icon_path)
        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=icon_path))

        self.root = root
        
        self.interface = interface

        # Initialize
        bd = 1

        main_frame = tk.Frame(root, background="bisque")
        tracker_frame = tk.Frame(main_frame, relief = tk.RIDGE, bd = bd)
        arduino_frame = tk.Frame(main_frame, relief = tk.RIDGE, bd = bd)
        button_frame = tk.Frame(main_frame, relief = tk.RIDGE, bd = bd)
        statusbar_frame = tk.Frame(main_frame, relief = tk.RIDGE, bd = bd)

        # Layout config
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        tracker_frame.grid(row=0, column=0, sticky="ew")
        arduino_frame.grid(row=0, column=1, sticky="nsew")
        button_frame.grid(row=1, column=0, columnspan=2)
        statusbar_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)


        # main_frame.pack(side="top", fill="both", expand=True)
        # tracker_frame.pack(side="left", fill="x", expand=True)
        # arduino_frame.pack(side="right", fill="x", expand=True)
        # button_frame.pack(side="bottom", fill="x", expand=True)
        # statusbar_frame.pack(side="bottom", fill="x", expand=True)
        
        # Add to instance
        self.main_frame = main_frame
        self.tracker_frame = tracker_frame
        self.arduino_frame = arduino_frame
        self.button_frame = button_frame
        self.statusbar_frame = statusbar_frame      

        # Initialize statusbar
        statusbar = tk.Label(self.statusbar_frame, text="Welcome to FReTs", relief=tk.SUNKEN, anchor=tk.W)
        statusbar.pack(side=tk.LEFT, fill=tk.X, expand = tk.YES)
        self.statusbar = statusbar

        # Initialize play button
        print(getattr(self.interface, 'play'))

        playButton = BetterButton(self.button_frame, 'play', self.interface.play, 0)
        pauseButton = BetterButton(self.button_frame, 'pause', self.interface.pause, 1)
        buttons = [playButton, pauseButton]

        # buttons = [BetterButton(self.button_frame, event_name, getattr(self.interface, event_name), index) for index, event_name in enumerate(['play', 'pause'])]
        [b.push() for b in buttons]
    
        # Initialize canvas (where the Arduino monitor is placed)
        canvas = tk.Canvas(self.arduino_frame, width = self.width//2, height = self.height//2, highlightthickness=0, bd=bd)
        canvas.width = self.width // 2
        canvas.height = self.height // 2
        canvas.pack(fill=tk.BOTH, expand=tk.YES)
        canvas.bind("<Button-1>", self.callback)
        canvas.bind("<Configure>", self.on_resize)
        self.canvas = canvas

        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_pad = 20
        self.tkinter_init = True
        self.video_height = None
        self.video_width = None
        self.tkinter_finished = False

        self.log = logging.getLogger(__name__)

    def on_resize(self,event):
        
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width)/self.canvas.width
        hscale = float(event.height)/self.canvas.height
        self.canvas.width = event.width
        self.canvas.height = event.height
        # resize the canvas
        self.canvas.scale("all",0,0,wscale,hscale)
        # rescale all the objects tagged with the "all" tag


    def callback(self, event):
        print("clicked at", event.x, event.y)

    def tkinter_preprocess(self, img, width):

        # print(self.width//2)
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=width)
        # print(image.shape)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image

    def tkinter_update_widget(self, img, name = "", preprocess=True):
        '''
        Update images/frames
        '''

        if preprocess:
            
            width = self.main_frame.winfo_width() // 2
            # self.log.debug('Main frame width is {}'.format(width))
            if width <= 1: width = self.width // 2

            image = self.tkinter_preprocess(img, width = width)

        if self.tkinter_init:
            label = tk.Label(self.tracker_frame, image=image)
            label.pack(side=tk.LEFT, anchor=tk.W)
            self.panel[name] = label

        else:
            self.panel[name].configure(image=image)
            self.panel[name].image = image

    
    def tkinter_update_monitor(self, mapping):
        '''
        Update the arduino monitor
        '''
        
        # check that the mapping is loaded (i.e. is not None)
        if mapping is not None:

            if self.tkinter_init:
                
                for i, pin in enumerate(mapping.itertuples()):
                    
                    label = tk.Label(self.canvas, text = pin.Index, fg = 'white', bg = 'black')
                    y = pin.x*60
                    x = 30 + pin.y * 60
                    label.place(x=x-15, y=y-30)
                    self.panel[i] = label
                    # circle is an integer indicating the index of the shape
                    # i.e. the first cirlce returns 1, the second 2 and so forth
                    circle = self.canvas.create_circle(x, y, 6, fill = "red")
                
                self.canvas.addtag_all("all")

            
            else:
                for i, pin in enumerate(mapping.itertuples()):
                    
                    state = self.interface.device.pin_state[pin.Index]
    
                    if type(state) is bool:
                        color = 'yellow' if state else 'red'
                    else:
                        color = 'blue'
                    self.canvas.itemconfig(i+1, fill = color)

    
    def tkinter_update_statusbar(self):
        '''
        Update statusbar
        '''

        c1 = self.interface.device.overview['start'] < self.interface.timestamp
        c2 = self.interface.device.overview['end'] > self.interface.timestamp
        selected_rows = c1 & c2
        active_blocks = self.interface.device.overview.index[selected_rows].tolist()
        text = 'Welcome to FReTs'
        if active_blocks:
            main_block = active_blocks[-1]
        else:
            self.statusbar['text'] = text
            return 0


        passed = self.interface.timestamp - self.interface.device.overview.loc[main_block]['start']
        left = self.interface.device.overview.loc[main_block]['end'] - self.interface.timestamp
        time_position = np.round(np.array([passed, left]) / 60, 3)


        text = 'Running ' + ' and '.join(active_blocks) + ' blocks'
        text += ' {}m passed, {}m left'.format(*time_position)
        self.statusbar['text'] = text


    def update(self):
         
        ## TODO rewrite to make less verbose
        ####################################
        ## TODO Separate initialization from update
        ####################################
        if self.interface.play_event.is_set() or True:
            if self.interface.track:
                self.tkinter_update_widget(img=self.interface.frame_color, name='frame_color')
                # self.tkinter_update_widget(img=self.interface.gray_gui, name='gray_gui')

            if self.interface.device:
                self.tkinter_update_monitor(self.interface.device.mapping)
                self.tkinter_update_statusbar()
    
            if self.tkinter_init:
                # # self.interface.tkinter_init = False
                self.root.wm_title("Learning memory stream")
                self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
                self.canvas.addtag_all("all")
                self.tkinter_init = False
                self.tkinter_finished = True
            # if self.interface.timestamp % 1 == 0:

        self.root.update_idletasks()
        # needed to close the window with X
        self.root.update()
        # print('One step')
        # self.interface.exit.wait(2)

        
        time.sleep(.01)
    
    def onClose(self):
        self.root.quit()
        self.interface.onClose()


    
