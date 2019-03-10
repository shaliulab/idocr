import numpy as np
import argparse
import datetime
import cv2
import time
import matplotlib.pyplot as plt
from pypylon import pylon
from pypylon import genicam


white = (255, 255, 255)
yellow = (0, 255, 255)
red = (0, 0, 255)
blue = (255, 0, 0)

cv2_version = cv2.__version__
 

class Arena():
    
    def __init__(self, contour, identity):
        """Initialize an arena object
        """
        
        self.contour = contour
        self.identity = identity
        self.min_arena_area = 1000
        self.block_size = 9
        self.param1 = 13
        
    def compute(self):
        #print("Contour area is:")
        #print(type(self.contour))
        #print(self.contour)
        self.area = cv2.contourArea(self.contour)
        self.X, self.Y, self.W, self.H = cv2.boundingRect(self.contour)
        M0 = cv2.moments(self.contour)
        if M0['m00'] != 0 and M0['m10']:
            self.CX1 = int(M0['m10']/M0['m00'])
            self.CY1 = int(M0['m01']/M0['m00'])
        else:
            pass
            # handle what happens when the if above is not true 
    
    def validate(self):
        
        if self.area < self.min_arena_area:
            return False
        else:
            return True
        
    def make_mask(self, gray):

        mask = np.full(gray.shape, 0, dtype = np.uint8)
        ## TODO:
        ## Give some room for cases where the fly might be by the edges. Expand the arena a few pixels!
        padding = 0
        y0 = self.Y - padding
        y1 = self.Y + self.H + padding

        x0 = self.X - padding
        x1 = self.X + self.W + padding
        mask[y0:y1, x0:x1] = 255
        self.mask = mask
        #self.mask = np.full(gray.shape, 255, dtype=np.uint8)

    def draw(self, img):
        """Draw the arena
        """
      
        print('Arena {} has an area of {}'.format(self.identity, self.area))
        cv2.putText(img, 'Arena '+ str(self.identity), (self.X - 50, self.Y - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        cv2.drawContours(img, [self.contour], 0, red, 1)
        cv2.rectangle(img, (self.X, self.Y), (self.X + self.W, self.Y + self.H), (0,255,255), 2)
        cv2.circle(img, (self.CX1, self.CY1), 2, blue, -1)
        
        return img

    def find_flies(self, gray, kernel):
        """A masked version of gray
        """
        transform = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.block_size, self.param1)
        #transform = cv2.morphologyEx(transform, cv2.MORPH_OPEN, kernel)
        self.mask_input = transform 

        if cv2_version[0] == '4':
            flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        transform = cv2.bitwise_and(transform, self.mask)
        self.mask_result = transform 

        return flies
 
    

class Fly():
    
    def __init__(self, arena, contour, identity):
        """Initialize fly object
        """
        
        self.contour = contour
        self.identity = identity
        self.arena  = arena
        self.min_object_length = 0
        self.min_obj_arena_dist = 2
        self.max_object_area = 200
        self.min_object_area = 0
        self.min_intensity = 80
    
    def compute(self):
        # compute area of the fly contour
        self.area = cv2.contourArea(self.contour)
        # compute the coordinates of the bounding box around the contour
        # https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        self.x, self.y, self.w, self.h = cv2.boundingRect(self.contour)
        # compute the length of the diagonal line between opposite corners of the bounding box
        self.diagonal = np.sqrt(self.w ** 2 + self.h ** 2) 

        # compute the center of the fly
        M1 = cv2.moments(self.contour)
        if M1['m00'] != 0 and M1['m10']:
            # used in the validation step
            self.cx1 = int(M1['m10']/M1['m00'])
            self.cy1 = int(M1['m01']/M1['m00'])
        else:
            # handle what happens when the if above is not true
            pass
    
    def validate(self, gray):
        """Validate fly by checking all requirements
        Returns True if all requirements are passed and False otherwise
        """

        # the diagonal needs to be greater than a minimum
        fly_passed_1 = self.diagonal > self.min_object_length
        # the intensity on the top left corner needs to be greater than a minimum 
        ## INCONGRUENT
        fly_passed_2 = gray[self.y, self.x] > self.min_intensity
        # the area has to be more than a minimum and less than a maximum
        fly_passed_3 = self.area > self.min_object_area
        fly_passed_4 = self.area < self.max_object_area

        ## DEBUG
        #print(self.area)
        #print(self.diagonal)
        #print(fly_passed_1)
        #print(fly_passed_2)
        #print(fly_passed_3)
        #print(fly_passed_4)

        if not (fly_passed_1 and fly_passed_2 and fly_passed_3 and fly_passed_4) or getattr(self, "cx1") is None:
                return False
        else:
            # the center of the fly contour needs to be within the contour of the arena it was found in
            # it has to be more than min_obj_arena_dist pixels from the arena contour (inside it)
            # if min_obj_arena_dist is 0, then it's fine if it borders the arena contour
            fly_passed_5 = cv2.pointPolygonTest(self.arena.contour, (self.cx1, self.cy1), True) > self.min_obj_arena_dist
            print(fly_passed_5)
            return fly_passed_5 
        
         
    
    def draw(self, img, frame_count):
        """Draw fly
        """
        
        print('Find fly {}'.format(self.identity))
        if self.identity > 1:
            cv2.putText(img, 'Error: more than one object found per arena', (25,40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, white, 1)

        cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), blue, 2)
        #print((self.x, self.y, self.x + self.w, self.y + self. h))
        print("Frame count is {}".format(frame_count))

        return img

    def save(self, frame_count, time_position):
        record = "\t".join(["{}"] * 10) + "\n"
        record.format(frame_count, time_position, self.arena.identity, self.identity,
                      self.cx1, self.cy1, self.arena.CX1, self.arena.CY1, self.cx1-self.arena.CX1, self.cy1-self.arena.CY1)
        return record


       

class Tracker():
   
    def __init__(self, camera="opencv", fps = 2, experimenter="Sayed", duration=1200, video=None, kernel_factor=5):
        """
        Setup video recording parameters.

        duration: in seconds
        """

                   
        self.duration = duration
        self.frame_count = 0
        self.missing_fly = 0
        now = datetime.datetime.now()
        self.Date_time = now.strftime("%Y_%m_%dT%H_%M_%S")
        self.record_to_save = ["\t".join(["Frame", "TimePos", "Arena",
                                         "FlyNo", "FlyPosX", "FlyPosY",
                                         "ArenaCenterX", "ArenaCenterY",
                                         "RelativePosX", "RelativePosY"]
                                       ) + "\n"]


        self.N = 10
        self.fps = fps
        self.kernel_factor = kernel_factor
        self.kernel = np.ones((kernel_factor, kernel_factor), np.uint8)


        # self.record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']

        stream = self.initialize_stream(camera, video)

        if self.fps is not None and video is not None:
            # Set the FPS of the camera
            stream.set_fps(self.fps)

        print("[INFO] Starting video ...")
        time.sleep(0.1)

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

    def initialize_stream(self, camera, video=None):
    
        if camera == "pylon":
            class Stream():
                def __init__(self):
                    print("[INFO] Starting a pylon camera!")

                    # The exit code of the sample application.
                    exitCode = 0
                    ## TODO
                    ## Check camera is visible!
                    cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
                    # Print the model name of the camera.
                    print("Using device ", cap.GetDeviceInfo().GetModelName())
                
                    # The parameter MaxNumBuffer can be used to control the count of buffers
                    # allocated for grabbing. The default value of this parameter is 10.
                    cap.MaxNumBuffer = 5
                
                    countOfImagesToGrab = 100
                    # Start the grabbing of c_countOfImagesToGrab images.
                    # The camera device is parameterized with a default configuration which
                    # sets up free-running continuous acquisition.
                    cap.StartGrabbingMax(countOfImagesToGrab)
                    self.cap = cap 

                def get_fps(self):
                    fps = self.cap.AcquisitionFrameRateAbs.GetValue()
                    return fps

                def get_width(self):
                    width = self.cap.Width.GetValue()
                    return width

                def get_height(self):
                    height = self.cap.Height.GetValue()
                    return height 


                def get_time_position(self, frame_count):
                    t = frame_count / self.get_fps()
                    return t

                def set_fps(self, fps):
                    self.stream.AcquisitionFrameRateAbs.SetValue(fps)

                def read_frame(self):
                    # Wait for an image and then retrieve it. A timeout of 5000 ms is used.
                    grabResult = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                    self.grabResult = grabResult
                    # Image grabbed successfully?
                    ret = grabResult.GrabSucceeded()
                    if ret:
                        # Access the image data.
                        #print("SizeX: ", grabResult.Width)
                        #print("SizeY: ", grabResult.Height)
                        img = grabResult.Array
                        return ret, img
                    return False, None

                def release(self):
                    self.grabResult.Release()
                    

        else:
            class Stream():
                def __init__(self):
                    s = 0 if video is None else video
                    if s == 0: print("[INFO] Capturing stream!")
                    if s != 0: print("[INFO] Opening {}!".format(s))
                    self.cap = cv2.VideoCapture(s)

                def get_fps(self):
                    fps = self.cap.get(5)
                    if fps == 0:
                        return 2
                    return fps

                def get_time_position(self, frame_count):
                    t = frame_count / self.get_fps()
                    return t
       
                def get_width(self):
                    width = int(self.cap.get(3))
                    return width
 
                def get_height(self):
                    height = int(self.cap.get(4))
                    return height 
 
                def set_fps(self, fps):
                    if self.get_fps() != fps:
                        print("[INFO] Setting fps to {}".format(fps))
                        self.cap.set(5, fps)
 
             #   def set_width(self, width):
             #       if self.stream.get_width() != width:
             #           self.stream.set(3, width)
             #   def set_height(self, height):
             #       if self.stream.get_height() != height:
             #           self.stream.set(4, height)

                def read_frame(self):
                    ret, img = self.cap.read()
                    return ret, img
               
                def release(self):
                    self.cap.release()

        stream = Stream()
        return stream


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

    def find_arenas(self, frame_count, gray, RangeLow1 = 0, RangeUp1 = 255, N = 10):
        """Performs Otsu thresholding followed by morphological transformations to improve the signal/noise.
        Input image is the average image
        Output is a tuple of length 2, where every elemnt is either a list of contours or None (if no contours were found)
        
        More info on Otsu thresholding: https://docs.opencv.org/3.4/d7/d4d/tutorial_py_thresholding.html
        
        frame_count: 0-indexed number of frames processed so far
        gray: Gray frame as output of read_frame()
        RangeLow1: value assigned to pixels below the Otsu threshold
        RangeUp1: value assigned to pixels above the Otsu threshold
        kernel_factor: size of the square kernel used in blurring and openings
        N: number of frames that must have passed for the program to search for arenas
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
                print('There are {} potential flies found in arena {}'.format(len(fly_contours), arena.identity))

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
                        print("Fly not validated")
                        continue
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

            cv2.namedWindow('result', cv2.WINDOW_NORMAL)
            cv2.imshow("result", img)
            cv2.resizeWindow('result', 800,800)

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

