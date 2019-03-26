# Standard library imports
import datetime
import logging
import os.path
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
setup_logging()

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

    # https://stackoverflow.com/questions/17985216/draw-circle-in-tkinter-python
    def create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)


class TkinterGui(ResizingCanvas):

    def __init__(self, interface):

        self.gui_width = None
        self.gui_pad = None
        self.log = None
        self.tkinter_init = None
        self.canvas = None
        self.interface = None
        self.panel = {}

        root = tk.Tk()
        # set initial size of window (800x800 and 500 pixels up)
        root.geometry("800x800+0-500")
        self.root = root

        # frame = tk.Frame(root)
        # frame.pack(fill=tk.BOTH, expand=tk.YES)
        
        
        canvas = ResizingCanvas(self.root, width=800, height=800, highlightthickness=0, bd=0, relief='ridge')
        canvas.pack(fill=tk.BOTH, expand=tk.YES, anchor = tk.NW)
        canvas.bind("<Button-1>", self.callback)
        
        statusbar = tk.Label(self.root, text="Welcome to FReTs", relief=tk.SUNKEN, anchor=tk.W)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar = statusbar

        # canvas.grid()
        # self.frame = frame
        self.canvas = canvas

        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_width = 250
        self.gui_pad = 20
        self.tkinter_init = True
        self.video_height = None
        self.video_width = None
        
        self.interface = interface
        self.log = logging.getLogger(__name__)

    def callback(self, event):
        print("clicked at", event.x, event.y)

    def tkinter_preprocess(self, img):
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=self.gui_width)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image

    def tkinter_update_widget(self, img, name = "", preprocess=True):

   
        if preprocess:
            image = self.tkinter_preprocess(img)

        if self.tkinter_init:
            label = tk.Label(self.canvas, image=image)
            label.pack(side=tk.LEFT, anchor=tk.N)
            self.panel[name] = label

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
                
                state = self.interface.device.pin_state[pin.Index]

                if type(state) is bool:
                    color = 'yellow' if state else 'red'
                else:
                    color = 'blue'
                self.canvas.itemconfig(i+1, fill = color)
    
    def tkinter_update_status(self):

        c1 = self.interface.device.overview['start'] < self.interface.timestamp
        c2 = self.interface.device.overview['end'] > self.interface.timestamp
        selected_rows = c1 & c2
        active_blocks = self.interface.device.overview.index[selected_rows].tolist()
        main_block = active_blocks[-1]

        passed = self.interface.timestamp - self.interface.device.overview.loc[main_block]['start']
        left = self.interface.device.overview.loc[main_block]['end'] - self.interface.timestamp
        time_position = np.round(np.array([passed, left]) / 60, 3)


        text = 'Running ' + ' and '.join(active_blocks) + ' blocks'
        text += ' {}m passed, {}m left'.format(*time_position)
        self.statusbar['text'] = text


    def update(self):
         
        ## TODO rewrite to make less verbose
        ####################################
        self.tkinter_update_widget(img=self.interface.frame_color, name='frame_color')
        self.tkinter_update_widget(img=self.interface.gray_gui, name='gray_gui')
        # self.tkinter_update_widget(img=self.monitor, y=self.gui_pad * 2 + * (self.gui_width + self.gui_pad), x=self.gui_pad * 2 + * (self.gui_width + self.gui_pad), preprocess=False)
        self.tkinter_update_monitor(self.interface.device.mapping)
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
    
    def onClose(self):
        self.root.quit()
        self.interface.onClose()


    
