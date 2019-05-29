# Standard library imports
import datetime
import logging
import sys
import threading
import time

# Third party imports
import coloredlogs
import cv2
import numpy as np
import yaml
from pathlib import Path

# Local application imports
from features import Arena, Fly
from streams import PylonStream, StandardStream, streams_dict
from lmdt_utils import setup_logging
from decorators import export

# Set up package configurations
cv2_version = cv2.__version__
setup_logging()
coloredlogs.install()

def crop_stream(img, crop):
    width = img.shape[1]
    fw = width//crop
    y0 = fw * (crop // 2)
    if len(img.shape) == 3:
        img = img[:,y0:(y0+fw),:]
    else:
        img = img[:,y0:(y0+fw)]
    return img




@export
class Tracker():
   
    def __init__(self, interface, camera = "opencv", video = None):
        """
        Setup video recording parameters.
        """

    

        # self.record_to_save = ["\t".join(["Frame", "TimePos", "Arena",
        #                                  "FlyNo", "FlyPosX", "FlyPosY",
        #                                  "ArenaCenterX", "ArenaCenterY",
        #                                  "RelativePosX", "RelativePosY"]
        #                                ) + "\n"]
        

        self.interface = None
        self.camera = None
        self.video = None

        self.frame_count = None
        self.record_frame_count = None
        self.old_found = None
        self.missing_fly = None

        # Initialization
        # Results variables
        self.arena_contours = None
        self.found_flies = None
        self.accuImage = None

        self.img = None
        self.transform = None
        self.gray_masked = None
        self.status = None

        self.arenas = None
        self.masks = None

        # Config variables
        self.stream = None
        self.fps = None
        self.block_size = None
        self.param1 = None
        self.crop = None
        self.kernel_factor = None
        self.kernel = None
        self.N = None

        # Assignment
        self.interface = interface
        self.camera = camera
        self.video = video


        # Results variables
        # how many flies are found in the whole experiment
        # in a perfect recording, it should be nframes x nflies/frame
        self.found_flies = 0
        # frames recorded since pressing play
        self.frame_count = 0
        # frames recorded since pressing record
        self.record_frame_count = 0
        # flies detected in the last frame
        self.old_found = 0
        # number of arenas where no fly was detected
        self.missing_fly = 0


        # Config variables
        self.fps = self.interface.cfg["tracker"]["fps"]
        self.block_size = self.interface.cfg["arena"]["block_size"]
        self.param1 = self.interface.cfg["arena"]["param1"]
        self.crop = self.interface.cfg["tracker"]["crop"]
        self.kernel_factor = self.interface.cfg["arena"]["kernel_factor"] 
        self.kernel = np.ones((self.kernel_factor, self.kernel_factor), np.uint8)
        self.N = self.interface.cfg["tracker"]["N"] 

        self.log = logging.getLogger(__name__)

        self.saver = self.interface.data_saver
        
        ## TODO
        ## Find a way to get camera.Width.SetValue(whatever) to work
        ## Currently returns error: the node is not writable
        # if VIDEO_WIDTH != 1280:
        #     cap.set(3, 1280)
        # if VIDEO_HEIGHT != 1024:
        #     cap.set(4, 1024)

        self.load_camera()
        self.init_image_arrays()

        self.status = True
 
        self.arenas = {}
        self.masks = {}

        self.log.info("Stream has shape w:{} h:{}".format(self.interface.video_width, self.interface.video_height))


        if self.fps and video:
            # Set the FPS of the camera
            self.stream.set_fps(self.fps)

    def load_camera(self):

        if self.video is not None:
            self.video = Path(self.video)
            if self.video.is_file():
                self.stream = streams_dict[self.camera](self.video.__str__())
            else:
                self.log.error("Video under provided path not found. Check for typos")
                sys.exit(1)
        else:
            self.stream = streams_dict[self.camera](0)

    def init_image_arrays(self):

        self.interface.video_width = self.stream.get_width() // self.crop
        self.interface.video_height = self.stream.get_height()

        # Make accuImage an array of size heightxwidthxnframes that will
        # store in the :,:,i element the result of the tracking for frame i
        self.accuImage = np.zeros((self.interface.video_height, self.interface.video_width, self.N), np.uint8)
        
        # self.img = np.zeros((self.interface.video_height, self.interface.video_width, 3), np.uint8)
        self.transform = np.zeros((self.interface.video_height, self.interface.video_width), np.uint8)
        self.gray_masked = np.zeros((self.interface.video_height, self.interface.video_width), np.uint8)

        self.interface.frame_color = np.zeros((self.interface.video_height, self.interface.video_width, 3), np.uint8)
        self.interface.gray_color = np.zeros((self.interface.video_height, self.interface.video_width, 3), np.uint8)
        self.interface.gray_gui = np.zeros((self.interface.video_height, self.interface.video_width), np.uint8)
        self.interface.stacked_arenas = np.zeros((self.interface.video_height, self.interface.video_width), np.uint8)



    def rotate_frame(self, img, rotation=180):
        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        rows, cols = img.shape[:2]
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
        img_rot = cv2.warpAffine(img, M, (cols,rows))
        return img_rot
 
    
    def annotate_frame(self, img):

        ## TODO Dont make coordinates of text hardcoded
        ###################################################
        cv2.putText(img,'Frame: '+ str(self.record_frame_count),   (25,25),    cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'Time: '+  str(int(self.interface.timestamp)), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
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
        self.accuImage[:,:,self.frame_count % self.N] = gray
        if self.frame_count > 1:   
            avgImage = np.average(self.accuImage[:,:,:self.frame_count], 2).astype('uint8')
        else:
            avgImage = self.accuImage[:,:,self.frame_count].astype('uint8')

        image_blur = cv2.GaussianBlur(avgImage, (self.kernel_factor, self.kernel_factor), 0)
        _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
        arena_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)
        if cv2_version[0] == '4':
            arena_contours, _ = cv2.findContours(arena_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, arena_contours, _ = cv2.findContours(arena_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return arena_contours

    def track(self):
        
        if not self.interface.exit.is_set():
            # Check if experiment is over
            if self.interface.timestamp > self.interface.duration:
                self.log.info("Experiment duration is reached. Closing")
                #self.save_record()
                return False

            # How much time has passed since we started tracking?
            if self.interface.record_start:
                self.interface.timestamp = (datetime.datetime.now() - self.interface.record_start).total_seconds()
            else:
                self.interface.timestamp = 0

            # Read a new frame
            ret, frame = self.stream.read_frame()

            # If ret is False, a new frame could not be read
            # Exit 
            if not ret:
                self.log.info("Stream or video is finished. Closing")
                self.onClose()
                self.interface.stream_finished = True
                return False
           
            frame = crop_stream(frame, self.crop)
            # Make single channel i.e. grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_color = frame  
            else:
                gray = frame.copy()
                gray_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            # Annotate frame
            frame_color = self.annotate_frame(gray_color)
            
            # Find arenas for the first N frames
            if self.frame_count < self.N and self.frame_count > 0 or not self.interface.arena_ok_event.is_set():
                self.arena_contours = self.find_arenas(gray)

            if self.arena_contours is None or len(self.arena_contours) == 0:
                self.log.debug("Frame #{} no arenas".format(self.frame_count))
                self.frame_count += 1
                status = self.track()
                return status

            transform = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.block_size, self.param1)
            self.transform = transform


            arenas_dict = {}

               
            # Initialize an arena identity that will be increased with 1
            # for every validated arena i.e. not on every loop iteration!
            id_arena = 1
            # For every arena contour detected

            for arena_contour in self.arena_contours:
                        
                # Initialize an Arena object
                
                arena = Arena(tracker = self, contour = arena_contour, identity = id_arena)
                # and compute parameters used in validation and drawing
                corners = arena.compute()
                # Validate the arena
                # If not validated, move on the next arena contour
                # i.e. ignore the current arena
                if not arena.validate():
                   # move on to next i.e. continue to the next iteration
                   # continue means we actually WON'T continue with the current arena
                   continue

               
                # If validated, keep analyzing the current arena
                frame_color = arena.draw(frame_color)

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
                id_fly = 1
                # For every arena contour detected
                for fly_contour in fly_contours:
                    # Initialize a Fly object
                    fly = Fly(tracker = self, arena = arena, contour = fly_contour, identity = id_fly)
                    # and compute parameters used in validation and drawing
                    fly.compute()
                    
                    # If not validated, move on the next fly contour
                    # i.e. ignore the current fly 
                    if not fly.validate(gray):
                        self.log.debug("Fly not validated")
                        continue
                    self.log.debug("Fly {} in arena {} validated with area {} and length {}".format(fly.identity, fly.arena.identity, fly.area, fly.diagonal))
                    self.saver.process_row(
                            d = {
                                "frame": self.frame_count, "timestamp": self.interface.timestamp,
                                "arena": arena.identity, "fly": fly.identity,
                                "cx": fly.x_corrected, "cy": fly.y_corrected,
                                "datetime": datetime.datetime.now()
                                },
                            key = "data",
                            )
                    self.found_flies += 1
                    
                    # Draw the fly
                    frame_color = fly.draw(frame_color, self.frame_count)

                    # Add the fly to the arena
                    arena.fly = fly
                  
                    # Update the id_fly to account for one more fly detected
                    id_fly += 1

                    if id_fly > 1:
                        self.log.debug("Arena {} in frame {}. Multiple flies found".format(arena.identity, self.frame_count))

                    ############################################
                    ## End for loop over all putative flies
                    ##
               
                # If still 1, it means that none of the fly contours detected
                # were validated, a fly was not found in this arena!
                if id_fly == 1:
                    self.missing_fly += 1
                    fname = Path(self.interface.cfg['tracker']['fail'], '{}_{}.tiff'. format(self.frame_count, arena.identity)).__str__()
                    gray_crop = gray[arena.tl_corner[1]:arena.br_corner[1], arena.tl_corner[0]:arena.br_corner[0]]
                    cv2.imwrite(fname, gray_crop)


                arenas_dict[id_arena] = arena
                # Update the id_arena to account for one more arena detected
                id_arena += 1


                ########################################
                ## End for loop over all putative arenas


            # Update GUI graphics
            self.interface.frame_color = frame_color

            # TODO: Make into utils function
            #self.interface.stacked_arenas = self.stack_arenas(arenas_dict)

            # Print warning if number of flies in new frame is not the same as in previous
            if self.old_found != self.found_flies:
                self.log.warning("Found {} flies in frame {}".format(self.found_flies, self.frame_count))
            self.old_found = self.found_flies
            self.found_flies = 0

            self.update_counts()


            return True

        #########################
        ## End if 
        ##

        else:
            #self.save_prompt()
            return None
        
    def update_counts(self):
        self.frame_count += 1
        
        if self.interface.record_event.is_set():
                self.record_frame_count += 1
        
        if self.frame_count % 100 == 0:
            self.log.info("Frame #{}".format(self.frame_count))






     
    def stack_arenas(self, arenas):

        gray_color = self.interface.gray_color

        
        def draw_stacked(a):
            # print(a.corners)
            hhwws = np.array([a.corners[1,:] - a.corners[0,:] for key, a in arenas.items()])
            max_h, max_w = np.max(hhwws, axis = 0)

            ROI = gray_color[a.corners[0][0]:max_h, a.corners[0][1]:max_w]
            if a.fly:
                arena_crop = a.fly.draw(ROI, relative_to_arena = True)
            else:
                arena_crop = ROI
            cv2.rectangle(arena_crop, (0, 0), arena_crop.shape, 128, 2)
            return arena_crop

        stacked_arenas = [draw_stacked(a) for key, a in arenas.items()]
        stacked_arenas = np.stack(stacked_arenas, axis=0).reshape((10, 2))
        return stacked_arenas

        
        # try: 
        #     
        # except:
        #     self.log.debug(a.corners.shape)
        #     

        
    def _run(self):

        self.status = self.track()

        while self.status and not self.interface.exit.is_set():                
            self.merge_masks()
            self.interface.gray_gui = cv2.bitwise_and(self.transform, self.main_mask)
            self.status = self.track()
            self.interface.exit.wait(.2)
        
        self.onClose()

        if not self.interface.exit.is_set():
            self.interface.exit.set()
            

    def run(self):

        tracker_thread = threading.Thread(
            name = "tracker_thread",
            target = self._run
        )
        
        self.interface.tracker_thread = tracker_thread
        tracker_thread.start()
        return None
        
    def onClose(self):
        self.stream.release()
        self.log.info("Tracking stopped")
        self.log.info("{} arenas in {} frames analyzed".format(20 * self.frame_count, self.frame_count))
        self.log.info("Number of arenas that fly is not detected in is {}".format(self.missing_fly))
        self.saver.store_and_clear('data')

        if not self.interface.exit.is_set(): self.interface.onClose()

    def merge_masks(self):
    
        masks = self.masks.values()
        if len(masks) != 0:
            masks = np.array(list(masks))
            main_mask = np.bitwise_or.reduce(masks)
        else:
            main_mask = np.full((self.interface.video_height, self.interface.video_width, 3), 255, dtype=np.uint8)
    
        self.main_mask = main_mask

if __name__ == "__main__":
    import argparse
    from .interface import Interface
    
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video")
    ap.add_argument("-c", "--camera", type = str, default = "opencv", help="Stream source")
    ap.add_argument("-g", "--gui",    type = str,                     help="tkinter/opencv")
    args = vars(ap.parse_args())
    
    interface = Interface(track = True, camera = args["camera"], video = args["video"], gui = args["gui"])
    interface.prepare()
    interface.start()


