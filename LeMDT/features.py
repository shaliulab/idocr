import numpy as np
import cv2

from lmdt_utils import setup_logging

white = (255, 255, 255)
yellow = (0, 255, 255)
red = (0, 0, 255)
blue = (255, 0, 0)

setup_logging()
cv2_version = cv2.__version__
 

class Arena():

    ## TODO
    ## Make config an argument that the user can change from the CLI
    def __init__(self, tracker, contour, identity, config = "config.yml"):
        """Initialize an arena object
        """
        self.tracker = tracker
        self.contour = contour
        self.identity = identity
        self.min_arena_area = self.tracker.interface.cfg["arena"]["min_area"] 
        self.area = None
        self.mask = None
        self.box = None
        self.fly = None
        self.tl_corner = None
        self.br_corner  = None
        self.corners = None
        self.dilation_kernel = np.ones((5,5),np.uint8)
        fly = None

    def __repr__(self):
        print("Arena(tracker = self, contour = arena_contour, identity = {})".format(self.identity))
        
    def compute(self):
        # try:
        self.area = cv2.contourArea(self.contour)
        # except:

        #self.x, self.y, self.w, self.h = cv2.boundingRect(self.contour)
        rect = cv2.minAreaRect(self.contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        self.box = box
        tl_corner = np.min(box, axis = 0)
        br_corner = np.max(box, axis = 0)

        self.tl_corner = tl_corner 
        self.br_corner = br_corner 

        #self.center = (self.x + self.w//2, self.y + self.h // 2)
        M0 = cv2.moments(self.contour)
        if M0['m00'] != 0 and M0['m10']:
            self.cx = int(M0['m10']/M0['m00'])
            self.cy = int(M0['m01']/M0['m00'])
            self.center = (self.cx, self.cy)
        else:
            pass
            # handle what happens when the if above is not true
        
        self.corners = np.array([tl_corner, br_corner])
        return self.corners

    def validate(self):
        
        if self.area < self.min_arena_area:
            return False
        else:
            return True
        
    def make_mask(self, shape):

        mask = np.full(shape, 0, dtype = np.uint8)
        cv2.drawContours(mask, [self.box], 0, white, -1)
        cv2.dilate(mask, self.dilation_kernel, iterations = 1)
        self.mask = mask
        return mask

    def draw(self, img):
        """
        Draw the arena
        """
      
        self.tracker.log.debug('Arena {} has an area of {}'.format(self.identity, self.area))
        cv2.putText(img, str(self.identity), (self.tl_corner[0] - 50, self.tl_corner[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        # Draw the actual contour
        cv2.drawContours(img, [self.contour], 0, red, 1)
        #cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), (0,255,255), 2)

        # Draw the detected box
        cv2.drawContours(img,[self.box], 0, yellow, 2)
        #cv2.circle(img, (self.cx, self.cy), 2, blue, -1)
        
        return img

    def find_flies(self, transform, kernel):
        #transform = cv2.morphologyEx(transform, cv2.MORPH_OPEN, kernel)

        if cv2_version[0] == '4':
            flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if len(flies) == 0:
            pass
            # try the edge insensitive method

        return flies
 
    

class Fly():
    
    ## TODO
    ## Make config an argument that the user can change from the CLI
    def __init__(self, tracker, arena, contour, identity, config = "config.yml"):
        """Initialize fly object
        """
       
        self.tracker = tracker
        self.contour = contour
        self.identity = identity
        self.arena  = arena


        self.min_object_length = self.tracker.interface.cfg["fly"]["min_length"]
        self.min_obj_arena_dist =  self.tracker.interface.cfg["fly"]["min_dist_arena"]
        self.max_object_area =  self.tracker.interface.cfg["fly"]["max_area"]
        self.min_object_area =  self.tracker.interface.cfg["fly"]["min_area"]
        self.min_intensity =  self.tracker.interface.cfg["fly"]["min_intensity"]

        self.x = None
        self.y = None
        self.w = None
        self.h = None
        self.diagonal = None
        self.arena_distance_x = None
        self.arena_distance_y = None
    
    def compute(self):
        # compute area of the fly contour
        self.area = cv2.contourArea(self.contour)
        # compute the coordinates of the bounding box around the contour
        # https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        self.x, self.y, self.w, self.h = cv2.boundingRect(self.contour)

        self.arena_distance_x = self.x - self.arena.tl_corner[0]
        self.arena_distance_y = self.y - self.arena.tl_corner[1]

        # compute the length of the diagonal line between opposite corners of the bounding box
        self.diagonal = np.sqrt(self.w ** 2 + self.h ** 2) 

        # compute the center of the fly
        M1 = cv2.moments(self.contour)
        if M1['m00'] != 0 and M1['m10']:
            # used in the validation step
            self.cx = int(M1['m10']/M1['m00'])
            self.cy = int(M1['m01']/M1['m00'])
            self.x_corrected = self.cx - self.arena.center[0]
            self.y_corrected = self.cy - self.arena.center[1]
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
        self.tracker.log.debug(fly_passed_1)
        self.tracker.log.debug(fly_passed_2)
        self.tracker.log.debug(fly_passed_3)
        self.tracker.log.debug(fly_passed_4)

        if not (fly_passed_1 and fly_passed_2 and fly_passed_3 and fly_passed_4) or getattr(self, "cx") is None:
                return False
        else:
            # the center of the fly contour needs to be within the contour of the arena it was found in
            # it has to be more than min_obj_arena_dist pixels from the arena contour (inside it)
            # if min_obj_arena_dist is 0, then it's fine if it borders the arena contour
            fly_passed_5 = cv2.pointPolygonTest(self.arena.contour, (self.cx, self.cy), True) > self.min_obj_arena_dist
            return fly_passed_5 
        
    def draw(self, img, frame_count, relative_to_arena=False):
        """Draw fly
        """
        
        if self.identity > 1:
            self.tracker.log.debug('Error: more than one object found per arena')

        if relative_to_arena:
            cv2.rectangle(img, (self.arena_distance_x, self.arena_distance_y), (self.arena_distance_x + self.w, self.arena_distance_y + self.h), blue, 2)
        else:
            cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), blue, 2)
        self.tracker.log.debug("tl: {},{}. br: {},{}".format(self.x, self.y, self.x + self.w, self.y + self. h))

        return img

    def save(self, frame_count, time_position):
        record = "\t".join(["{}"] * 10) + "\n"
        record.format(frame_count, time_position, self.arena.identity, self.identity,
                      self.cx, self.cy, self.arena.cx, self.arena.cy, self.cx-self.arena.cx, self.cy-self.arena.cy)
        return record
