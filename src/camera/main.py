from .features import Arena, Fly
from .streams import PylonStream, StandardStream
from src.saver.main import Saver
from PIL import ImageTk, Image
import yaml
import datetime
import numpy as np
from pypylon import pylon
from pypylon import genicam
import threading
import argparse
import cv2
import imutils
import sys
import logging, coloredlogs
coloredlogs.install()
import tkinter as tk
Frame = tk.Frame
cv2_version = cv2.__version__

streams_dict = {"pylon": PylonStream, "opencv": StandardStream}

def crop_stream(img, crop):
    width = img.shape[1]
    fw = width//crop
    y0 = fw * (crop // 2)
    if len(img.shape) == 3:
        img = img[:,y0:(y0+fw),:]
    else:
        img = img[:,y0:(y0+fw)]
    return img



class Tracker(Frame):
   
    def __init__(self, camera = "opencv", duration = 1200, video = None, config = "config.yml", gui=False):
        """
        Setup video recording parameters.
        duration: in seconds
        """



        with open(config, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

                   
        self.experimenter = cfg["tracker"]["experimenter"]
        self.duration = duration
        self.missing_fly = 0
        now = datetime.datetime.now()
        self.Date_time = now.strftime("%Y_%m_%dT%H_%M_%S")
        self.record_to_save = ["\t".join(["Frame", "TimePos", "Arena",
                                         "FlyNo", "FlyPosX", "FlyPosY",
                                         "ArenaCenterX", "ArenaCenterY",
                                         "RelativePosX", "RelativePosY"]
                                       ) + "\n"]


        self.N = 10
        self.fps = cfg["tracker"]["fps"]
        kernel_factor = cfg["arena"]["kernel_factor"] 
        self.kernel = np.ones((kernel_factor, kernel_factor), np.uint8)
        self.kernel_factor = kernel_factor
        self.found_flies = 0
        self.old_found = 0
        self.gui = gui
        self.arena_contours = None
        self.block_size = cfg["arena"]["block_size"]
        self.param1 = cfg["arena"]["param1"]
        self.crop = cfg["tracker"]["crop"]
        # tkinter variables
        # based on https://www.pyimagesearch.com/2016/05/30/displaying-a-video-feed-with-opencv-and-tkinter/
        self.gui_width = 250
        self.gui_pad = 20
        

        # self.record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']

        stream = streams_dict[camera](video)


        if self.fps is not None and video is not None:
            # Set the FPS of the camera
            stream.set_fps(self.fps)

        self.log = logging.getLogger(__name__)
        self.log.info("Starting video ...")

        self.saver = Saver(store = cfg["tracker"]["store"], cache = {})

        # Extract 
        #VIDEO_POS = cap.get(0)
        #VIDEO_FRAME = cap.get(1)
        #VIDEO_WIDTH = stream.get_width()
        #VIDEO_HEIGHT = stream.get_height()
        #VIDEO_FPS = cap.get(5)
        #VIDEO_RGB = cap.get(16)
        
        ## TODO
        ## Find a way to get camera.Width.SetValue(whatever) to work
        ## Currently returns error: the node is not writable
        # if VIDEO_WIDTH != 1280:
        #     cap.set(3, 1280)
        # if VIDEO_HEIGHT != 1024:
        #     cap.set(4, 1024)


        # Make accuImage an array of size heightxwidthxnframes that will
        # store in the :,:,i element the result of the tracking for frame i
        video_width = stream.get_width() // self.crop
        video_height = stream.get_height()
        self.video_width = video_width
        self.video_height = video_height
        self.log.info("Stream has shape w:{} h:{}".format(video_width, video_height))
        self.accuImage = np.zeros((video_height, video_width, self.N), np.uint8)
        self.stream = stream
        self.time_position = 0
        self.frame_count = 0
        self.img = np.full((self.video_height, self.video_width, 3), 0, np.uint8)
        self.transform = np.full((self.video_height, self.video_width), 0, np.uint8)
        self.gray_masked = np.full((self.video_height, self.video_width), 0, np.uint8)
 


        if self.gui:
            self.log.info("Initializing GUI")
            self.tkinter_initialize()



    def rotate_frame(self, img, rotation=180):
        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        rows, cols = img.shape[:2]
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
        img_rot = cv2.warpAffine(img, M, (cols,rows))
        return img_rot
 
    
    def annotate_frame(self, img):

        ## TODO Dont make coordinates of text hardcoded
        ###################################################
        cv2.putText(img,'Frame: '+ str(self.frame_count),   (25,25),    cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'Time: '+  str(self.time_position), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'LEFT',                        (25,525),   cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'RIGHT',                       (1100,525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        return img

    def find_arenas(self, gray, RangeLow1 = 0, RangeUp1 = 255):
        """Performs Otsu thresholding followed by morphological transformations to improve the signal/noise.
        Input image is the average image
        Output is a tuple of length 2, where every elemnt is either a list of contours or None (if no contours were found)
        
        More info on Otsu thresholding: https://docs.opencv.org/3.4/d7/d4d/tutorial_py_thresholding.html
        
        gray: Gray frame as output of read_frame()
        RangeLow1: value assigned to pixels below the Otsu threshold
        RangeUp1: value assigned to pixels above the Otsu threshold
        kernel_factor: size of the square kernel used in blurring and openings
        """

        # assign the grayscale to the ith frame in accuImage
        self.accuImage[:,:,self.frame_count] = gray     
        avgImage = np.average(self.accuImage[:,:,:self.frame_count], 2).astype('uint8')
        image_blur = cv2.GaussianBlur(avgImage, (self.kernel_factor, self.kernel_factor), 0)
        _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
        arena_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)
        if cv2_version[0] == '4':
            arenas, _ = cv2.findContours(arena_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, arenas, _ = cv2.findContours(arena_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        self.arenas = arenas
        return self.arenas

       
    def save_record(self, input_save_name=None):
        filename = '_'.join([e if e is not None else '' for e in [self.Date_time, input_save_name]]) + ".txt"
        #filename = "{}.txt".format(self.Date_time)
        with open(filename, 'w') as f:
            for rowrecord in self.record_to_save:
                f.write(rowrecord)
        return None

                  
    def save_prompt(self):
                
        input_save = input("Do you want to save the file? (y/n) ")
        if input_save in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
            input_save1 = input("Do you want to add file name to the default one? (y/n) ")
            input_save_name = None
            if input_save1 in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                input_save_name = input("Please write your own filename: ")
            save_record(input_save_name)



    def track(self):
        
        stop_event = getattr(self, "stopEvent", None)
        event_stop = False 

        if stop_event is threading.Event:
            event_stop = not x.is_set()

        if not event_stop:
            # Check if experiment is over
            if self.time_position > self.duration:
                self.log.info("Experiement duration is reached. Closing")
                self.save_record()
                return False

            # How much time has passed since we started tracking?
            time_position = self.stream.get_time_position(self.frame_count)
            self.time_position = time_position

            # Read a new frame
            ret, img = self.stream.read_frame()

            # If ret is False, a new frame could not be read
            # Exit 
            if not ret:
                self.log.info("Stream or video is finished. Closing")
                self.onClose(x=False)
                self.stop = True
                return False
           
            img = crop_stream(img, self.crop)
            # Make single channel i.e. grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  
            else:
                gray = img.copy()

            # Annotate frame
            img = self.annotate_frame(img)
            
            # Find arenas for the first N frames
            if self.frame_count < self.N and self.frame_count > 0:
                self.arena_contours = self.find_arenas(gray)

            if self.arena_contours is None:
                self.log.warning("Frame #{} no arenas".format(self.frame_count))
                self.frame_count += 1
                status = self.track()
                return status

            transform = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.block_size, self.param1)
            self.transform = transform

            ## DEBUG
            ## Initialize an arena dictionary to keep track of the found arenas
            self.arenas = {}
            self.masks = {}

           
            # Initialize an arena identity that will be increased with 1
            # for every validated arena i.e. not on every loop iteration!
            id_arena = 0
            # For every arena contour detected

            for arena_contour in self.arena_contours:
                        
                # Initialize an Arena object
                arena = Arena(self, arena_contour, id_arena)
                # and compute parameters used in validation and drawing
                arena.compute()
                # Validate the arena
                # If not validated, move on the next arena contour
                # i.e. ignore the current arena
                if not arena.validate():
                   # move on to next i.e. continue to the next iteration
                   # continue means we actually WON'T continue with the current arena
                   continue
               
                # If validated, keep analyzing the current arena
                img = arena.draw(img)

                # Make a mask for this arena
                ## TODO Right now the masking module does not work
                ## and is not required either
                mask = arena.make_mask(gray.shape[:2])

                ## DEBUG
                ## Add the arena to the dictionary
                self.arenas[arena.identity] = arena
                self.masks[arena.identity] = mask 

                ## Find flies in this arena
                gray_masked = cv2.bitwise_and(self.transform, mask)
                fly_contours = arena.find_flies(gray_masked, self.kernel)
                #print('There are {} potential flies found in arena {}'.format(len(fly_contours), arena.identity))

                # Initialize a fly identity that will be increased with 1
                # for every validated fly i.e. not on every loop iteration!
                id_fly = 0
                # For every arena contour detected
                for fly_contour in fly_contours:
                    # Initialize a Fly object
                    fly = Fly(self, arena, fly_contour, id_fly)
                    # and compute parameters used in validation and drawing
                    fly.compute()
                    # If not validated, move on the next fly contour
                    # i.e. ignore the current fly 
                    if not fly.validate(gray):
                        self.log.debug("Fly not validated")
                        continue
                    self.log.debug("Fly {} in arena {} validated with area {} and length {}".format(fly.identity, fly.arena.identity, fly.area, fly.diagonal))
                    self.saver.process_row(
                            d = {"frame": self.frame_count, "time": self.time_position, "arena": arena.identity, "fly": fly.identity, "cx": fly.cx, "cy": fly.cy},
                            key = "df",
                            )
                    self.found_flies += 1
                    
                    # Draw the fly
                    img = fly.draw(img, self.frame_count)

                    # Save the fly
                    self.record_to_save.append(fly.save(self.frame_count, self.time_position))
                    
                    # Update the id_fly to account for one more fly detected
                    id_fly += 1

                    if id_fly > 1:
                        self.log.warning("Arena {} in frame {}. Multiple flies found".format(arena.identity, self.frame_count))

                    ############################################
                    ## End for loop over all putative flies
                    ##
               
                # If still 0, it means that none of the fly contours detected
                # were validated, a fly was not found in this arena!
                if id_fly == 0:
                    self.missing_fly += 1


                # Update the id_arena to account for one more arena detected
                id_arena += 1

                ########################################
                ## End for loop over all putative arenas

            self.frame_count +=1
            self.img = img
            if self.frame_count % 100 == 0:
                self.log.info("Frame #{}".format(self.frame_count))

            if self.old_found != self.found_flies:
                self.log.debug("Found {} flies in frame {}".format(self.found_flies, self.frame_count))
            self.old_found = self.found_flies
            self.found_flies = 0


            return True

        #########################
        ## End if 
        ##

        else:
            self.save_prompt()
            self.log.info("Number of frames that fly is not detected in is {}".format(self.missing_fly))
            return None

    def run(self, init=False):
        status = self.track()

        if status:
            self.merge_masks()
            self.gray_gui = cv2.bitwise_and(self.transform, self.main_mask)

            if self.gui:
                self.tkinter_update('img', 0, 0, gui_width = (self.gui_width + self.gui_pad) * 2)
                #self.tkinter_update('main_mask', 0, 1)
                self.tkinter_update('gray_gui', 0, 2)
                self.init = False
                self.root.after(10, self.run)
                # set a callback to handle when the window is closed
                if init:
                    self.root.wm_title("Learning memory stream")
                    self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
                    self.root.mainloop()
            else:
                cv2.imshow("img", self.img)
                #cv2.imshow("mask", self.main_mask)
                #cv2.imshow('transform', self.transform)
                cv2.imshow("gray_gui", self.gray_gui)
                # Check if user forces leave (press q)
                keypress_stop = cv2.waitKey(1) & 0xFF in [27, ord('q')]
                if not keypress_stop and status:
                    self.run()
                self.onClose()
                return False
        else:
            self.onClose(x=False)
            return False


    def tkinter_initialize(self):
        self.stopEvent = None
        self.root = tk.Tk()
        w = self.gui_width * 3 + self.gui_pad * 6
        self.log.info("GUI Window size is set to {}x800".format(w))
        self.root.geometry("{}x800".format(w))
        Frame.__init__(self, self.root)

        self.panel = np.full((1,3), None)
        #print(self.panel.shape)
        #print(self.panel[0,0])
        self.init = True
        self.pack(fill=tk.BOTH, expand=1)

        # start a thread that constantly pools the video sensor for
        # the most recently read frame
        self.stopEvent = threading.Event()
        #self.thread = threading.Thread(name="Track thread", target=self.track, args=())
        #self.thread.start()
        #self.run()

        

    def tkinter_preprocess(self, img, gui_width):
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = imutils.resize(image, width=gui_width)
        image = Image.fromarray(image)
        image = ImageTk.PhotoImage(image)
        return image




    def tkinter_update(self, img, i, j, gui_width = None):

        if gui_width is None:
            gui_width = self.gui_width

        img = getattr(self, img, False)

        image = self.tkinter_preprocess(img, gui_width)

        if self.init:
            label = tk.Label(image=image)
            self.panel[i,j] = label
            self.panel[i,j].image = image
            x = self.gui_pad * (j + 1) + j * (gui_width + self.gui_pad)
            y = self.gui_pad * (i + 1) + i * (self.gui_width + self.gui_pad)
            label.place(x = x, y = y)
        else:
            self.panel[i,j].configure(image=image)
            self.panel[i,j].image = image

 

    def onClose(self, x=True):
        for k, lst in self.saver.cache.items():  # you can instead use .iteritems() in python 2
            self.saver.store_and_clear(lst, k)

        if x:
            self.log.info("User manually exited app. Closing...")
        if self.gui:
            # set the stop event, cleanup the camera, and allow the rest of
            # the quit process to continue
            self.stopEvent.set()
            self.stream.release()
            self.root.quit()
            #self.root.destroy()

        else:
            self.stream.release()
            cv2.destroyAllWindows()

        self.stop = True
        self.save_record()
        self.log.info("{} frames analyzed".format(self.frame_count))
        sys.exit(1)

    def merge_masks(self):
    
        masks = self.masks.values()
        if len(masks) != 0:
            masks = np.array(list(masks))
            main_mask = np.bitwise_or.reduce(masks)
        else:
            main_mask = np.full(self.img.shape[:2], 255, dtype=np.uint8)
    
        self.main_mask = main_mask


if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video")
    ap.add_argument("--gui", action = 'store_true')
    args = vars(ap.parse_args())
    tracker = Tracker(video=args["video"], gui=args["gui"])
    if not args["gui"]: tracker.run()
