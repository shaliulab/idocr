import numpy as np
import argparse
import datetime
import cv2
import time
import matplotlib.pyplot as plt

white = (255, 255, 255)
yellow = (0, 255, 255)
red = (0, 0, 255)
blue = (255, 0, 0)
 

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
        y0 = self.Y - 10
        y1 = self.Y + self.H + 10

        x0 = self.X - 10
        x1 = self.X + self.W + 10
        mask[y0:y1, x0:x1] = 255
        self.mask = mask
        #self.mask = np.full(gray.shape, 255, dtype=np.uint8)

    def draw(self, img):
        """Draw the arena
        """
      
        print('Arena {} has an area of {}'.format(self.identity, self.area))
        cv2.putText(img, 'Arena '+ str(self.identity), (self.X - 50, self.Y - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        cv2.drawContours(img, [self.contour], 0, (255,255,0), 1)
        cv2.rectangle(img, (self.X, self.Y), (self.X + self.W, self.Y + self.H), (0,255,255), 2)
        cv2.circle(img, (self.CX1, self.CY1), 2, (255,0,0), -1)
        
        return img

    def find_flies(self, gray, kernel):
        """A masked version of gray
        """
        transform = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.block_size, self.param1)
        #transform = cv2.morphologyEx(transform, cv2.MORPH_OPEN, kernel)
        self.mask_input = transform 
        (_, flies, _) = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
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
        self.min_obj_arena_dist = 5
        self.max_object_area = 200
        self.min_object_area = 0
        self.min_intensity = 80
    
    def compute(self):
        self.area = cv2.contourArea(self.contour)
        self.x, self.y, self.w, self.h = cv2.boundingRect(self.contour)
        self.diagonal = np.sqrt(self.w ** 2 + self.h ** 2) 

        M1 = cv2.moments(self.contour)
        if M1['m00'] != 0 and M1['m10']:
            # used in the validation step
            self.cx1 = int(M1['m10']/M1['m00'])
            self.cy1 = int(M1['m01']/M1['m00'])
        else:
            pass
            # handle what happens when the if above is not true
    
    def validate(self, gray):
        fly_passed_1 = self.diagonal > self.min_object_length
        fly_passed_2 = gray[self.x, self.y] < self.min_intensity
        fly_passed_3 = self.area > self.min_object_area
        fly_passed_4 = self.area < self.max_object_area
        print(self.area)
        print(self.diagonal)
        
        print(fly_passed_1)
        print(fly_passed_2)
        print(fly_passed_3)
        print(fly_passed_4)

        if not (fly_passed_1 and fly_passed_2 and fly_passed_3 and fly_passed_4) or getattr(self, "cx1") is None:
                return False
        else:
            fly_passed_5 = cv2.pointPolygonTest(self.arena.contour, (self.cx1, self.cy1), True) < self.min_obj_arena_dist
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

    def save_record(self, frame_count, time_position):
        record = "\t".join(["{}"] * 10) + "\n"
        record.format(frame_count, time_position, self.arena.identity, self.identity,
                      self.cx1, self.cy1, self.arena.CX1, self.arena.CY1, self.cx1-self.arena.CX1, self.cy1-self.arena.CY1)
        return record
        

class Tracker():
   
    def __init__(self, experimenter="Sayed", duration=1200, path_to_video=None, path_to_frame=None, kernel_factor=5):
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
        self.fps = 2
        self.kernel_factor = kernel_factor
        self.kernel = np.ones((kernel_factor, kernel_factor), np.uint8)


        # dst = cv2.warpAffine(img, M, (VIDEO_WIDTH,VIDEO_HEIGHT))
#         self.record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']


        # cam_fps = cap.get(cv2.CAP_PROP_FPS)

        if path_to_frame is None:
            # reading a stream
            if path_to_video is None:
                print("[INFO] starting video stream...")
                cap = cv2.VideoCapture(0)
                time.sleep(0.1)
                VIDEO_POS = cap.get(0)
                VIDEO_FRAME = cap.get(1)
                VIDEO_WIDTH = cap.get(3)
                VIDEO_HEIGHT = cap.get(4)
                VIDEO_FPS = cap.get(5)
                VIDEO_RGB = cap.get(16)

                if VIDEO_WIDTH != 1280:
                    cap.set(3, 1280)
                if VIDEO_HEIGHT != 1024:
                    cap.set(4, 1024)
                cap.set(5, self.fps)
                time.sleep(0.1)
                
                self.source = "s"


            # otherwise, grab a reference to the video file
            else:
                # reading a video
                cap = cv2.VideoCapture(path_to_video)
                self.source = "v"

            self.cap = cap
            self.cam_fps = cap.get(5)

            # Make accuImage an array of size heightxwidthxnframes that will
            # store in the :,:,i element the result of the tracking for frame i
            self.accuImage = np.zeros((int(cap.get(4)), int(cap.get(3)), self.N), np.uint8)
                   
        elif path_to_video is None:
            # reading a single image
            self.source = "f"
            self.path_to_frame = path_to_frame
            self.cam_fps = 1

        else:
            raise Exception("You supplied both a video and a frame")


    def read_frame(self, frame_count=0, rotation=180):
        """Read a frame from the stream, rotate, grayscale and annotate
        Returns the rotated image with annotation and the grayscale
        """
        
        
        # Read
        if self.source != "f":
            ret, img_180 = self.cap.read()
        
        elif frame_count == 0:
            img_180 = cv2.imread(self.path_to_frame)
            ret = True
        else:
            img_180 = None
            ret = False

        # if ret is False (not ret), the stream is over and we can exit the while loop
        if not ret:
            return ret, img_180


        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        rows, cols = img_180.shape[:2]
        M = cv2.getRotationMatrix2D((cols/2, rows/2), rotation, 1)
        img = cv2.warpAffine(img_180, M, (cols,rows))

        return ret, img
    
    def annotate_frame(self, img, frame_count):
        time_position = frame_count/self.cam_fps

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

        if frame_count < N:
            # assign the grayscale to the ith frame in accuImage
            self.accuImage[:,:,frame_count] = gray     
            avgImage = np.average(self.accuImage[:,:,:frame_count], 2).astype('uint8')
            image_blur = cv2.GaussianBlur(avgImage, (self.kernel_factor, self.kernel_factor), 0)
            _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
            arena_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)
            (_, arenas, _) = cv2.findContours(arena_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            self.arenas = arenas
        return self.arenas

                  
    def save1(self, img, time_position):
                
#         input_save = input("Do you want to save the file? (y/n) ")
        input_save = "Y"
        if input_save in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
            input_save1 = input("Do you want to add file name to the default one? (y/n) ")
            if input_save1 in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                input_save_name = input("Please write your own filename: ")
                filename = "{}_{}.txt".format(input_save_name, self.Date_time)
                with open(filename, 'w') as f:
                    for rowrecord in self.record_to_save:
                        f.write(rowrecord)
                return None
            else:
                filename = "{}.txt".format(self.Date_time)
                with open(filename, 'w') as f:
                    for rowrecord in self.record_to_save:
                        f.write(rowrecord)
                return None
        
    def save2(self, img, time_position):
        filename = "{}.txt".format(self.Date_time)
        with open(filename, 'w') as f:
            for rowrecord in self.record_to_save:
                f.write(rowrecord)

            
        
        
    def track(self):
        frame_count = 0
        
        while 1:
            time.sleep(.2)    
            time_position = frame_count/self.cam_fps
            ret, img = self.read_frame(frame_count)
            # Make single channel i.e. grayscale
            if not ret:
                break
            
            cv2.imshow("stream", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  
            cv2.imshow("gray", gray)

                   
            img = self.annotate_frame(img, frame_count)

            if frame_count < self.N:
                arena_contours = self.find_arenas(frame_count, gray)

                   
            id_arena = 0

            self.arenas = {}
            if arena_contours is None:
                print("No arenas found in frame {}".format(frame_count))
                continue

            for arena_contour in arena_contours:
                         
                arena = Arena(arena_contour, id_arena)
                arena.compute()
                if not arena.validate():
                   continue
    
                arena.make_mask(gray)
                self.arenas[arena.identity] = arena

                fly_contours = arena.find_flies(gray, self.kernel)
                print('There are {} potential flies found in arena {}'.format(len(fly_contours), arena.identity))

                img = arena.draw(img)
                id_fly = 0

                for fly_contour in fly_contours:
                    fly = Fly(arena, fly_contour, id_fly)
                    moment_defined = fly.compute()
                    if not fly.validate(gray):
                        print("Fly not validated")
                        continue
                    id_fly += 1
                    img = fly.draw(img, frame_count)
                    self.record_to_save.append(fly.save_record(frame_count, time_position))

                if id_fly == 0:
                    self.missing_fly += 1

                id_arena += 1
                
            ####################
            if frame_count > self.N+1:
                print(self.arenas)

                cv2.imshow("mask_input", self.arenas[0].mask_input)
                cv2.moveWindow("mask_input", 40,30)

                mask = np.full(self.arenas[0].mask.shape, 0, np.uint8)
                mask_result = np.full(mask.shape, 0, np.uint8)
                
                for a in self.arenas.values():
                    print(a.mask_result.dtype)
                    mask_result = cv2.add(mask_result, a.mask_result)
                    mask = cv2.add(mask_result, a.mask)
                cv2.imshow("mask", mask)
                cv2.moveWindow("mask", 200,30)
                cv2.imshow("mask_result", mask_result)
                cv2.moveWindow("mask_result", 40,230)

            if frame_count == 40:
                cv2.waitKey(0)




            if cv2.waitKey(1) & 0xFF in [27, ord('q')]:
                self.save1(img, time_position)
                break

            elif time_position > self.duration:
                self.save2(img, time_position)
                break

            frame_count +=1
            
            
            cv2.imshow('image', img)
        print("Number of frames that fly is not detected in is {}".format(self.missing_fly))
        if self.source != "f": self.cap.release()
        cv2.destroyAllWindows()               
        return img


if __name__ == "__main__":

    tracker = Tracker(path_to_video="new_20x/20x.avi")
    tracker.track()

