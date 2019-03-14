from src.Camera.features import Arena, Fly
from src.Camera.streams import PylonStream, StandardStream
import yaml
import datetime
import numpy as np
from pypylon import pylon
from pypylon import genicam
import cv2
cv2_version = cv2.__version__

streams_dict = {"pylon": PylonStream, "opencv": StandardStream}

class Tracker():
   
    def __init__(self, camera = "opencv", duration = 1200, video = None, config = "config.yml"):
        """
        Setup video recording parameters.
        duration: in seconds
        """

        with open(config, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

                   
        self.experimenter = cfg["tracker"]["experimenter"]
        self.duration = duration
        #self.frame_count = 0
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


        # self.record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']

        stream = streams_dict[camera](video)

        if self.fps is not None and video is not None:
            # Set the FPS of the camera
            stream.set_fps(self.fps)

        print("[INFO] Starting video ...")

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



        self.stream = stream


        # Make accuImage an array of size heightxwidthxnframes that will
        # store in the :,:,i element the result of the tracking for frame i
        video_width = stream.get_width()
        video_height = stream.get_height()
        print("[INFO] frame width is {}".format(video_width))
        print("[INFO] frame height is {}".format(video_height))
        self.accuImage = np.zeros((video_height, video_width, self.N), np.uint8)

    def rotate_frame(self, img, rotation=180):
        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        rows, cols = img.shape[:2]
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
        img_rot = cv2.warpAffine(img, M, (cols,rows))
        return img_rot
 
    
    def annotate_frame(self, img, frame_count, time_position):

        ## TODO Dont make coordinates of text hardcoded
        ###################################################
        cv2.putText(img,'Frame: '+ str(frame_count),   (25,25),    cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'Time: '+  str(time_position), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'LEFT',                        (25,525),   cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        cv2.putText(img,'RIGHT',                       (1100,525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        return img

    def find_arenas(self, frame_count, gray, RangeLow1 = 0, RangeUp1 = 255):
        """Performs Otsu thresholding followed by morphological transformations to improve the signal/noise.
        Input image is the average image
        Output is a tuple of length 2, where every elemnt is either a list of contours or None (if no contours were found)
        
        More info on Otsu thresholding: https://docs.opencv.org/3.4/d7/d4d/tutorial_py_thresholding.html
        
        frame_count: 0-indexed number of frames processed so far
        gray: Gray frame as output of read_frame()
        RangeLow1: value assigned to pixels below the Otsu threshold
        RangeUp1: value assigned to pixels above the Otsu threshold
        kernel_factor: size of the square kernel used in blurring and openings
        """

        # assign the grayscale to the ith frame in accuImage
        self.accuImage[:,:,frame_count] = gray     
        avgImage = np.average(self.accuImage[:,:,:frame_count], 2).astype('uint8')
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

        
        frame_count = 0
        while 1:

            # How much time has passed since we started tracking?
            time_position = self.stream.get_time_position(frame_count)

            # Read a new frame
            ret, img = self.stream.read_frame()

            # If ret is False, a new frame could not be read
            # Exit 
            if not ret:
                print("[INFO] Stream or video is finished")
                break
            
           
            # Make single channel i.e. grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  
            else:
                gray = img.copy()

            # Annotate frame
            img = self.annotate_frame(img, frame_count, time_position)
            
            # Find arenas for the first N frames
            if frame_count < self.N:
                arena_contours = self.find_arenas(frame_count, gray)

            ## DEBUG
            ## Initialize an arena dictionary to keep track of the found arenas
            self.arenas = {}

            if arena_contours is None:
                print("No arenas found in frame {}".format(frame_count))
                continue
            
            # Initialize an arena identity that will be increased with 1
            # for every validated arena i.e. not on every loop iteration!
            id_arena = 0
            # For every arena contour detected
            for arena_contour in arena_contours:
                        
                # Initialize an Arena object
                arena = Arena(arena_contour, id_arena)
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
                arena.make_mask(gray)

                ## DEBUG
                ## Add the arena to the dictionary
                self.arenas[arena.identity] = arena

                ## Find flies in this arena
                fly_contours = arena.find_flies(gray, self.kernel)
                #print('There are {} potential flies found in arena {}'.format(len(fly_contours), arena.identity))

                # Initialize a fly identity that will be increased with 1
                # for every validated fly i.e. not on every loop iteration!
                id_fly = 0
                # For every arena contour detected
                for fly_contour in fly_contours:
                    # Initialize a Fly object
                    fly = Fly(arena, fly_contour, id_fly)
                    # and compute parameters used in validation and drawing
                    fly.compute()
                    # If not validated, move on the next fly contour
                    # i.e. ignore the current fly 
                    if not fly.validate(gray):
                        #print("Fly not validated")
                        continue
                    print("Fly validated in arena {}".format(fly.arena.identity))
                    # Draw the fly
                    img = fly.draw(img, frame_count)

                    # Save the fly
                    self.record_to_save.append(fly.save(frame_count, time_position))
                    
                    # Update the id_fly to account for one more fly detected
                    id_fly += 1
               
                # If still 0, it means that none of the fly contours detected
                # were validated, a fly was not found in this arena!
                if id_fly == 0:
                    self.missing_fly += 1


                # Update the id_arena to account for one more arena detected
                id_arena += 1
                
#            ####################
#            if frame_count > self.N+1:
#                print(self.arenas)
#
#                cv2.imshow("mask_input", self.arenas[0].mask_input)
#                cv2.moveWindow("mask_input", 40,30)
#
#                mask = np.full(self.arenas[0].mask.shape, 0, np.uint8)
#                mask_result = np.full(mask.shape, 0, np.uint8)
#                
#                for a in self.arenas.values():
#                    print(a.mask_result.dtype)
#                    mask_result = cv2.add(mask_result, a.mask_result)
#                    mask = cv2.add(mask_result, a.mask)
#                cv2.imshow("mask", mask)
#                cv2.moveWindow("mask", 200,30)
#                cv2.imshow("mask_result", mask_result)
#                cv2.moveWindow("mask_result", 40,230)
#
#            if frame_count == 40:
#                cv2.waitKey(0)


            # Check if user forces leave (press q)
            if cv2.waitKey(1) & 0xFF in [27, ord('q')] :
                self.save_prompt()
                break

            # Check if experiment is over
            elif time_position > self.duration:
                self.save_record()
                break

            frame_count +=1

            #cv2.namedWindow('result', cv2.WINDOW_NORMAL)
            cv2.imshow("result", img)
            #cv2.resizeWindow('result', 800,800)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
 
        ## while loop end
        #########################

        self.stream.release()
        cv2.destroyAllWindows()               
        print("Number of frames that fly is not detected in is {}".format(self.missing_fly))
        return None



 


if __name__ == "__main__":

    tracker = Tracker(path_to_video="new_20x/20x.avi")
    tracker.track()
