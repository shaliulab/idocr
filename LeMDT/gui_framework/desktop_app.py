# Standard library imports
import datetime
import logging
import os.path
from pathlib import Path
import sys
import time
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog

# Third party imports   
import cv2
import imutils
import numpy as np
from PIL import ImageTk, Image

# Local application imports
from lmdt_utils import setup_logging
from LeMDT import PROJECT_DIR, ROOT_DIR, STATIC_DIR

setup_logging()
log = logging.getLogger(__name__)

def _create_circle(self, x, y, r, **kwargs):
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle = _create_circle


class BetterButton(tk.Button):
    def __init__(self, parent, filename, command, index, **kwargs):
        """
        Create a tk.Button with automatic image addition
        """
        self.index = index
        photoimage = self.generate_image(filename)
        tk.Button.__init__(self, parent, image = photoimage, command = command, **kwargs)
        self.image = photoimage
                
    def generate_image(self, filename):
        """
        Take an image in the static/ folder and
        return a PhotoImage object of this image
        """

        fname = Path(STATIC_DIR,  filename+'.png').__str__()
        log.debug("Reading image on path {}".format(fname))
        if not os.path.isfile(fname):
            log.warning('Could not find {}. Are you sure it is in /static?'.format(fname))
            fname = Path(STATIC_DIR, 'question.png').__str__()
            photoimage = ImageTk.PhotoImage(file=fname)
        else:
            photoimage = ImageTk.PhotoImage(file=fname)
        return photoimage

    def push(self):
        self.grid(row=0, column = self.index, padx = 10)


class TkinterGui():

    def __init__(self, interface):

        self.gui_pad = None
        self.log = None
        self.init = None
        self.canvas = None
        self.interface = None
        self.panel = {}
        self.statusbar_text = None

        root = tk.Tk()
        root.style = ttk.Style()
        root.style.theme_use("clam")

        # set initial size of window (800x800 and 500 pixels up)
        self.height = 800
        self.width = 800

        root.geometry("{}x{}+200+200".format(self.width, self.height))
        icon_path = Path(STATIC_DIR, 'fly.png').__str__()
        # root.iconbitmap(icon_path)
        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=icon_path))
        
        self.root = root
        self.interface = interface
        self.bd = 1

        self.create_menu()
        self.configure_layout()
        self.configure_buttons()
        self.create_canvas()

        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_pad = 20
        self.init = True
        self.video_height = None
        self.video_width = None
        self.finished = False

        self.log = log


    def create(self):
        """
        Initialize the GUI
        """
        self.log.info('Initializing graphical interface')
        self.root.wm_title("LeMFT")
        self.root.wm_protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.addtag_all("all")

        # init tracker frame
        wshape = (self.height, self.width)
        init_tracker_frame = np.zeros(shape=wshape, dtype=np.uint8)
        label = tk.Label(self.tracker_frame, image=self.preprocess(init_tracker_frame, wshape[1]//2))
        label.pack(side=tk.LEFT, anchor=tk.W)
        self.panel['frame_color'] = label


        # init arduino control
        if self.interface.arduino:
            for i, pin in enumerate(self.interface.device.mapping.itertuples()):
                label = tk.Label(self.canvas, text = pin.Index, fg = 'white', bg = 'black')
                y = pin.x*60
                x = 30 + pin.y * 60
                label.place(x=x-15, y=y-30)
                self.panel[i] = label
                # circle is an integer indicating the index of the shape
                # i.e. the first cirlce returns 1, the second 2 and so forth
                circle = self.canvas.create_circle(x, y, 6, fill = "red")

        # Initialize statusbar
        self.statusbar_text = "Welcome to LeMDT"
        statusbar = tk.Label(self.statusbar_frame, text=self.statusbar_text, relief=tk.SUNKEN, anchor=tk.W)
        statusbar.pack(side=tk.LEFT, fill=tk.X, expand = tk.YES)
        self.statusbar = statusbar

        
        self.canvas.addtag_all("all")


    def create_menu(self):
        # creating a menu instance
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        # create the file object)
        file_menu = tk.Menu(self.menu)
        
        # adds a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        file_menu.add_command(label="Program", command=self.ask_program)
        file_menu.add_command(label="Mapping", command=self.ask_mapping)


        #added "file" to our menu
        self.menu.add_cascade(label="File", menu=file_menu)

    def configure_layout(self):
        main_frame = tk.Frame(self.root)
        bd = self.bd
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
        button_frame.grid(row=1, column=0, columnspan=3)
        statusbar_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Add to instance
        self.main_frame = main_frame
        self.tracker_frame = tracker_frame
        self.arduino_frame = arduino_frame
        self.button_frame = button_frame
        self.statusbar_frame = statusbar_frame
    
    def configure_buttons(self):
        """
        Initialize buttons
        """
        playButton = BetterButton(self.button_frame, 'play', self.interface.play, 1)
        okButton = BetterButton(self.button_frame, 'ok_arena', self.interface.ok_arena, 2)
        recordButton = BetterButton(self.button_frame, 'record', self.interface.record, 3)

        buttons = [playButton, okButton, recordButton]
        [b.push() for b in buttons]

    
    def create_canvas(self):
        """
        Initialize canvas (where the Arduino monitor is placed)
        """
        bd = self.bd
        canvas = tk.Canvas(self.arduino_frame, width=self.width//2, height=self.height//2, highlightthickness=0, bd=bd)

        canvas.width = self.width // 2
        canvas.height = self.height // 2
        canvas.pack(fill=tk.BOTH, expand=tk.YES)
        canvas.bind("<Button-1>", self.on_click)
        canvas.bind("<Configure>", self.on_resize)
        self.canvas = canvas
   
    def ask_program(self, filetype='program'):
        """
        Select a file in the /program dir to provide a program or paradigm
        Once a valid file is selected, the program is loaded
        This is the callback function of the program submenu in the file menu
        """
        initialdir = Path(PROJECT_DIR, filetype+'s').__str__()
        program_path = tk.filedialog.askopenfilename(
            initialdir = initialdir,title = "Select {} file".format(filetype),
            filetypes = (("csv files","*.csv"),("all files","*.*"))
            )
        if program_path != ():
            self.interface.load_program_event.set()
            self.interface.device.program_path = program_path
            self.interface.device.prepare('exit')
            self.log.info('Loading program {}'.format(self.interface.program_path))



    def ask_mapping(self):
        initialdir = Path(PROJECT_DIR, 'mappings').__str__()
        self.interface.mapping_path = tk.filedialog.askopenfilename(
            initialdir = initialdir,title = "Select mapping file",
            filetypes = (("csv files","*.csv"),("all files","*.*"))
            )
        self.log.info('Loading mapping {}'.format(self.interface.mapping_path))



    def on_resize(self,event):
        """

        """
        
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width)/self.canvas.width
        hscale = float(event.height)/self.canvas.height
        self.canvas.width = event.width
        self.canvas.height = event.height
        # resize the canvas
        self.canvas.scale("all",0,0,wscale,hscale)
        # rescale all the objects tagged with the "all" tag


    def on_click(self, event):
        self.log.info("clicked at {} {}".format(event.x, event.y))

    def preprocess(self, img, width):
        """
        Resize an image to a arget width
        and wrap it in a PhotoImage class
        """

        # print(self.width//2)
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=width)
        # print(image.shape)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image

    def update_widget(self, img):
        """
        Update images/frames
        """
            
        width = self.main_frame.winfo_width() // 2
        # self.log.debug('Main frame width is {}'.format(width))
        if width <= 1: width = self.width // 2

        image = self.preprocess(img, width=width)
        self.panel['frame_color'].configure(image=image)
        self.panel['frame_color'].image = image

    
    def update_monitor(self, mapping):
        """
        Update the arduino monitor
        """       
        for i, pin in enumerate(mapping.itertuples()):

            state = self.interface.device.pin_state[pin.Index]
            if type(state) is bool:
                color = 'yellow' if state else 'red'
            else:
                color = 'blue'
            self.canvas.itemconfig(i+1, fill = color)

    
    def update_statusbar(self):
        '''
        Update statusbar
        '''
        ## Improve messages in the statusbar
        ## It should warn when the next event is coming
        ## TODO REFACTOR

        if self.interface.arduino and self.interface.record_event.is_set():
            c1 = self.interface.device.overview['start'] < self.interface.timestamp
            c2 = self.interface.device.overview['end'] > self.interface.timestamp
            selected_rows = c1 & c2
            active_blocks = self.interface.device.overview.index[selected_rows].tolist()
            if active_blocks:
                main_block = active_blocks[-1]
                passed = self.interface.timestamp - self.interface.device.overview.loc[main_block]['start']
                left = self.interface.device.overview.loc[main_block]['end'] - self.interface.timestamp
                time_position = np.round(np.array([passed, left]) / 60, 3)
                text = 'Running ' + ' and '.join(active_blocks) + ' blocks'
                text += ' {}m passed, {}m left'.format(*time_position)
                self.statusbar['text'] = text
            else:
                self.statusbar['text'] = self.statusbar_text
        elif self.interface.arena_ok_event.is_set():
            self.statusbar['text'] = "Fixing arena contours and stopping further detection"

        elif self.interface.play_event.is_set():
            self.statusbar['text'] = 'Running tracker @ {} fps'.format(self.interface.tracker.sampled_fps)

        # else:
        #     self.statusbar['text'] = 'Recording without Arduino paradigm for {} seconds'.format(int(self.interface.timestamp))


    def apply_updates(self):
        self.root.update_idletasks()
        ## needed to close the window with X
        self.root.update()

    def run(self):
        '''
        Run the tkinter GUI

        1.- Update the statusbar
        2.- If track is True, update the tracking widget i.e. the processed frame
        3.- If arduino is True, update the arduino monitor
        '''
         
        ## TODO rewrite to make less verbose
        ####################################
        ## TODO Separate initialization from updatez
        ####################################

        self.update_statusbar()
        if self.interface.track:
            self.update_widget(img=self.interface.frame_color)
        
        if self.interface.arduino:
            self.update_monitor(self.interface.device.mapping)              

        self.apply_updates()
    
    def close(self):
        """
        Quit the GUI and run the interface.close() method
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """
        self.root.quit()
        self.interface.close()


    
