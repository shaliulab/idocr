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
from tkinter import simpledialog

# Third party imports   
import cv2
import imutils
import numpy as np
import pandas as pd
from PIL import ImageTk, Image

# Local application imports
from lmdt_utils import setup_logging, _toggle_pin
from LeMDT import PROJECT_DIR, ROOT_DIR, STATIC_DIR
from decorators import if_record_event


setup_logging()
log = logging.getLogger(__name__)

def _create_circle(self, x, y, r, **kwargs):
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle = _create_circle

# a subclass of Canvas for dealing with resizing of windows
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
        self.scale("all",0,0,wscale,hscale)
        # print("canvas size: {}x{}".format(self.height, self.width))

    
    def create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)


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
        # print("self.index/3")
        # print(self.index/3)
        self.place(relx=self.index/3, anchor="nw")


class TkinterGui():

    def __init__(self, interface):

        HEIGHT = 1000
        WIDTH = 1000
        self.width = WIDTH
        self.height = HEIGHT
        self.gui_pad = None
        self.log = None
        self.init = None
        self.canvas = None
        self.interface = None
        self.panel = {}
        self.statusbar_text = None
        self.circles = {}
        self.zoom_frame_columns = None

        root = tk.Tk(className='learningmemorysetup')
        canvas = tk.Canvas(root, height=HEIGHT, width=WIDTH)
        canvas.pack()
        self.main_canvas = canvas
        
        # set initial size of window (800x800 and 500 pixels up)
        
        # root.geometry("{}x{}+200+200".format(self.width, self.height))
        icon_path = Path(STATIC_DIR, 'fly.png').__str__()
        # root.iconbitmap(icon_path)
        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=icon_path))

        # self.root.grid_rowconfigure(0, weight=1)
        # self.root.grid_columnconfigure(0, weight=1)
        # self.root.grid_columnconfigure(1, weight=1)


        self.root = root
        self.interface = interface
        self.control_panel_path = Path(PROJECT_DIR, 'arduino_panel', self.interface.cfg["interface"]["filename"]).__str__()

        self.bd = 1

        ####################################
        ## MENU 
        ####################################
        
        # Add the menu entries for the program and mapping files

        # create a menu (topbar) instance
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        
        # create the file object
        file_menu = tk.Menu(self.menu)
        # add a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        file_menu.add_command(label="Program", command=self.load_program)
        file_menu.add_command(label="Mapping", command=self.ask_mapping)
        # add "file" to our menu
        self.menu.add_cascade(label="File", menu=file_menu)

        
        
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

        self.arena_width = self.interface.cfg["arena"]["width"]
        self.arena_height = self.interface.cfg["arena"]["height"]
        


    def create(self):
        """
        Fire up a Tkinter window

        Set its name, shape, a statusbar and a control monitor for the Arduino

        Called by interface.init_components() method,
        upon starting the Python software
        """
        self.log.info('Initializing graphical interface')
        self.root.wm_title("LeMDT")
        self.root.wm_protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.addtag_all("all")



        # init tracker frame
        wshape = (self.height, self.width)
        init_tracker_frame = np.zeros(shape=wshape, dtype=np.uint8)
        label = tk.Label(self.tracker_frame, image=self.preprocess(init_tracker_frame, wshape[1]//2))
        label.pack()
        self.panel['frame_color'] = label

        # Init zoom tab
        self.init_zoom_tab()



        # init arduino control
        if self.interface.arduino:
            control_panel = pd.read_csv(self.control_panel_path, skip_blank_lines=True, comment="#")
            radius = 6
            sym = control_panel["sym"].values
            # print(sym)
            pad_y = .05*self.canvas.height

            non_symmetric_pins = control_panel.loc[np.bitwise_not(sym)]
            x_values = np.array([.15, .45]) * self.canvas.width
            y_values = np.array([.1, .2, .35, 0.5, .65, .8, .95]) * self.canvas.height
    
            for i, pin in enumerate(non_symmetric_pins.itertuples()):
                
                # circle is an integer indicating the index of the shape
                # i.e. the first circle returns 1, the second 2 and so forth
                # third number is the radius   
                TEXT = pin.rendered_text
                circle = self.canvas.create_circle(x_values[pin.column], y_values[pin.row], radius, fill = "red", tags = ["clickable", pin.pin_id])
                self.canvas.create_text((x_values[pin.column], y_values[pin.row] + pad_y), text = TEXT)
                self.circles[pin.pin_id] = circle
                
            symmetric_pins = control_panel.loc[sym]

            for i, pin in enumerate(symmetric_pins.itertuples()):
                
                # circle is an integer indicating the index of the shape
                # i.e. the first circle returns 1, the second 2 and so forth
                # third number is the radius   
                
                self.canvas.create_circle(x_values[pin.column], y_values[pin.row], radius, fill = "red", tags = ["clickable", pin.pin_id])
                self.circles[pin.pin_id] = circle
                TEXT = "_".join(pin.pin_id.split("_")[:2])
                self.canvas.create_text((x_values[pin.column], y_values[pin.row] + pad_y), text = TEXT)
            
            self.canvas.tag_bind("clickable", "<1>", self.circle_click)

            



        # Initialize statusbar
        self.statusbar_text = "Welcome to LeMDT"
        statusbar = tk.Label(self.statusbar_frame, text=self.statusbar_text)
        statusbar.pack(fill="x", expand = tk.YES)
        self.statusbar = statusbar

        
        self.canvas.addtag_all("all")


    def configure_layout(self):
        """
        Arrange the elements of the GUI
        Called by __init__
        """
        self.nb = ttk.Notebook(self.root)
        self.nb.place(relx = 0, rely=0, relheight = 1, relwidth = 1, anchor="nw")
        main_frame = tk.Frame(self.nb, bg="#80c1ff", bd=self.bd)
        main_frame.place(relx=0, rely=0, relheight=1,relwidth=1)
        
        zoom_frame = tk.Frame(self.nb, bg="#80c1ff", bd=self.bd)
        zoom_frame.place(relx=0, rely=0, relheight=1,relwidth=1)
        zoom_frame_first_column = tk.Frame(zoom_frame)
        zoom_frame_first_column.place(relx=0,rely=0, relheight=1, relwidth=.5)
        zoom_frame_second_column = tk.Frame(zoom_frame)
        zoom_frame_second_column.place(relx=.5,rely=0, relheight=1, relwidth=.5)
        self.zoom_frame_columns = [zoom_frame_first_column, zoom_frame_second_column]
        
        tracker_frame = tk.Frame(main_frame, bg = "#000000")
        arduino_frame = tk.Frame(main_frame, bg = "#F0D943")
        button_frame = tk.Frame(main_frame)
        statusbar_frame = tk.Frame(main_frame)

        # Layout config
        tracker_frame.place(relx=0,rely=0, relheight=0.75, relwidth=0.75, anchor="nw")
        arduino_frame.place(relx=0.75,rely=0, relheight=0.75, relwidth=0.25, anchor="nw")
        
        button_frame.place(relx=0.25, rely=.75, relheight=0.2, relwidth=0.5, anchor="nw")
        statusbar_frame.place(relx=0, rely=.95, relheight=0.05, relwidth=1, anchor="nw")
        
        # Add to instance
        self.main_frame = main_frame
        self.zoom_frame = zoom_frame
        self.tracker_frame = tracker_frame
        self.arduino_frame = arduino_frame
        self.button_frame = button_frame
        self.statusbar_frame = statusbar_frame

        self.nb.add(self.main_frame, text = "Monitor")
        self.nb.add(self.zoom_frame, text = "Zoom")

    
    def configure_buttons(self):
        """
        Initialize buttons
        Called by __init__
        """
        
        playButton = BetterButton(self.button_frame, 'play', self.interface.play, 0)
        okButton = BetterButton(self.button_frame, 'ok_arena', self.interface.ok_arena, 1)
        recordButton = BetterButton(self.button_frame, 'record', self.interface.record, 2)

        buttons = [playButton, okButton, recordButton]
        [b.pack(side="left", expand=True, padx=10) for b in buttons]

    
    def create_canvas(self):
        """
        Initialize canvas (where the Arduino monitor is placed)
        Called by __init__
        """
        
        bd = self.bd
        canvas = ResizingCanvas(self.arduino_frame, highlightthickness=0, bd=bd)
        canvas.pack(fill=tk.X)
        # canvas.bind("<Button-1>", self.on_click)
        # canvas.bind("<Configure>", self.on_resize)
        self.canvas = canvas
   
    def ask_program(self):
        """
        Select a file in the /program dir to provide a program or paradigm
        Once a valid file is selected, the program is loaded
        """
        initialdir = Path(PROJECT_DIR, 'programs').as_posix()
        program_path = tk.filedialog.askopenfilename(
            initialdir = initialdir,title = "Select program file",
            filetypes = (("csv files","*.csv"),("all files","*.*"))
            )
        return program_path
        
    def load_program_callback(self):
        """
        This is the callback function of the program submenu in the file menu
        """

        threads = self.load_program()
        self.interface.device.threads = threads
        
    def load_program(self, program_path = None):
        """
        A helper function of ask_program that takes the program_path
        the user selected in the GUI and actually loads it into memory
        This is the callback function of the program submenu in the file menu
        """

        if program_path is None:
            program_path = self.ask_program()
        if program_path != ():
            self.interface.load_program_event.set()
            self.interface.device.program_path = program_path
            threads = self.interface.device.prepare('exit')
            self.log.info('Loading program {}'.format(self.interface.device.program_path))
            return threads


    def ask_mapping(self):
        """
        Select a file in the /mapping dir to provide a 'mapping' i.e.
        a link between the pin numbers on Arduino and the corresponding components
        they are connected to:
          example
          -------
             pin 10 = ODOUR A LEFT
             pin 11 = ODOUR A RIGHT
             ...
        """
        initialdir = Path(PROJECT_DIR, 'mappings').__str__()
        self.interface.mapping_path = tk.filedialog.askopenfilename(
            initialdir = initialdir,title = "Select mapping file",
            filetypes = (("csv files","*.csv"),("all files","*.*"))
            )
        self.log.info('Loading mapping {}'.format(self.interface.mapping_path))

    def on_click(self, event):
        """
        Callback function when clicking anywhere on the canvas
        """
        self.log.info("clicked at {} {}".format(event.x, event.y))
        item = self.canvas.find_closest(event.x, event.y)
        # print(item)
        # print(self.canvas.type(item))

    
    def circle_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        pin_id = self.canvas.gettags(item)[1]
        device=self.interface.device
        self.toggle_pin(device=device, pin_id=pin_id, value=1-device.pin_state[pin_id], thread=False)


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

    def init_zoom_tab(self):

        labels = [None,] * len(self.interface.stacked_arenas)

        for i, image in enumerate(self.interface.stacked_arenas):
            column = self.zoom_frame_columns[0]
            if i > 9:
                column = self.zoom_frame_columns[1]

            label = tk.Label(
                column, image=ImageTk.PhotoImage(Image.fromarray(image)),
            )
            label.pack(anchor="w")
            labels[i] = label
            
        self.panel['stacked_arenas'] = labels

    def update_zoom(self):
        for i, image in enumerate(self.interface.stacked_arenas):
            img = ImageTk.PhotoImage(Image.fromarray(image))
            self.panel["stacked_arenas"][i].configure(image = img)
            self.panel["stacked_arenas"][i].image = img
    
    def update_monitor(self, mapping):
        """
        Update the arduino monitor
        It goes through all the pins in the mapping
        and fetches their state.
        Then the corresponding circles are colored according to the stae
        """       
        for i, pin in enumerate(mapping.itertuples()):

            state = self.interface.device.pin_state[pin.Index]
            if type(state) is bool or type(state) is int:
                color = 'yellow' if state else 'red'
            elif type(state) is float:
                color = 'grey'
            else:
                color = 'blue'
            self.canvas.itemconfig(i*2-1, fill = color)

    
    def update_statusbar(self):
        '''
        Update statusbar with informative messages.
        '''

        # WARNING
        # This code is fragile because it relies on the index
        # of program being the row number
        # If that changes, the code breaks
        # The bug shows up when running the first non startup block

        # only if there is an arduino board and we are already recording
        if self.interface.arduino and self.interface.record_event.is_set():

            if self.interface.cfg['interface']['mode'] == 'debug' and self.interface.tracker.frame_count == 100:
                raise Exception

            # find the block(s) being executed right now
            # usually this is just startup (which runs always) and one other block
            c1 = self.interface.device.program['start'] < self.interface.timestamp
            c2 = self.interface.device.program['end'] > self.interface.timestamp
            # only rows fulfilling both requirements are running now
            selected_rows = c1 & c2
            # get the index of these blocks
            active_blocks = self.interface.device.program.index[selected_rows].tolist()
            if active_blocks:
                # usually there are two active blocks and startup is always the first
                # pick the last one
                main_block = active_blocks[-1]
                # get their names (startup + x)
                active_blocks_name = [self.interface.device.program['block'][b] for b in active_blocks]
                
                # find the start and end of this block
                block_start = self.interface.device.program.loc[main_block]['start']
                block_end = self.interface.device.program.loc[main_block]['end']

                # based on that, compute how much time has passed since start
                # and how much is left
                time_passed = self.interface.timestamp - block_start
                time_left = block_end - self.interface.timestamp
                # transform the amount of seconds into HH:MM:SS format
                time_position = list(map(lambda x: datetime.timedelta(seconds=round(x)), [time_passed, time_left]))

                # Display a meaningful messaage
                text = 'Running ' + ' and '.join(active_blocks_name) + ' blocks'
                text += ' {}m passed, {}m left'.format(*time_position)
                self.statusbar['text'] = text
            else:
                self.statusbar['text'] = self.statusbar_text
        elif self.interface.arena_ok_event.is_set():
            self.statusbar['text'] = "Fixed arena contours. Detection of arenas is complete"

        elif self.interface.play_event.is_set():
            self.statusbar['text'] = 'Running tracker @ {} fps'.format(self.interface.tracker.sampled_fps)

    def apply_updates(self):
        """
        Reflect all changes in the GUI
        Called by gui.run()
        """
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
            self.update_zoom()
        
        if self.interface.arduino:
            self.update_monitor(self.interface.device.mapping)              

        self.apply_updates()
    
    def close(self):
        """
        Quit the GUI and run the interface.close() method
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """

        self.interface.answer = simpledialog.askstring('Save results?', 'Yes/No')
        self.root.quit()
        self.interface.close()


TkinterGui.toggle_pin = _toggle_pin