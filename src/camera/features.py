import numpy as np
import argparse
import datetime
import cv2
import time
import matplotlib.pyplot as plt
from pypylon import pylon
from pypylon import genicam
import yaml


white = (255, 255, 255)
yellow = (0, 255, 255)
red = (0, 0, 255)
blue = (255, 0, 0)

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
        ## cfg
        cfg = self.tracker.cfg
        self.min_arena_area = cfg["arena"]["min_area"] 
        
    def compute(self):
        self.area = cv2.contourArea(self.contour)
        self.x, self.y, self.w, self.h = cv2.boundingRect(self.contour)
        M0 = cv2.moments(self.contour)
        if M0['m00'] != 0 and M0['m10']:
            self.cx = int(M0['m10']/M0['m00'])
            self.cy = int(M0['m01']/M0['m00'])
        else:
            pass
            # handle what happens when the if above is not true 
    
    def validate(self):
        
        if self.area < self.min_arena_area:
            return False
        else:
            return True
        
    def make_mask(self, shape):

        mask = np.full(shape, 0, dtype = np.uint8)
        ## TODO:
        ## Give some room for cases where the fly might be by the edges. Expand the arena a few pixels!
        padding = 0
        y0 = self.y - padding
        y1 = self.y + self.h + padding

        x0 = self.x - padding
        x1 = self.x + self.w + padding
        mask[y0:y1, x0:x1] = 255
        self.mask = mask
        return mask
        #self.mask = np.full(gray.shape, 255, dtype=np.uint8)

    def draw(self, img):
        """Draw the arena
        """
      
        self.tracker.log.debug('Arena {} has an area of {}'.format(self.identity, self.area))
        cv2.putText(img, 'Arena '+ str(self.identity), (self.x - 50, self.y - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        cv2.drawContours(img, [self.contour], 0, red, 1)
        cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), (0,255,255), 2)
        cv2.circle(img, (self.cx, self.cy), 2, blue, -1)
        
        return img

    def find_flies(self, transform, kernel):
        #transform = cv2.morphologyEx(transform, cv2.MORPH_OPEN, kernel)

        if cv2_version[0] == '4':
            flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, flies, _ = cv2.findContours(transform, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

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

        cfg = self.tracker.cfg

        self.min_object_length = cfg["fly"]["min_length"]
        self.min_obj_arena_dist =  cfg["fly"]["min_dist_arena"]
        self.max_object_area =  cfg["fly"]["max_area"]
        self.min_object_area =  cfg["fly"]["min_area"]
        self.min_intensity =  cfg["fly"]["min_intensity"]
    
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
            self.cx = int(M1['m10']/M1['m00'])
            self.cy = int(M1['m01']/M1['m00'])
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
        
         
    
    def draw(self, img, frame_count):
        """Draw fly
        """
        
        if self.identity > 1:
            cv2.putText(img, 'Error: more than one object found per arena', (25,40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, white, 1)

        cv2.rectangle(img, (self.x, self.y), (self.x + self.w, self.y + self.h), blue, 2)
        self.tracker.log.debug("tl: {},{}. br: {},{}".format(self.x, self.y, self.x + self.w, self.y + self. h))

        return img

    def save(self, frame_count, time_position):
        record = "\t".join(["{}"] * 10) + "\n"
        record.format(frame_count, time_position, self.arena.identity, self.identity,
                      self.cx, self.cy, self.arena.cx, self.arena.cy, self.cx-self.arena.cx, self.cy-self.arena.cy)
        return record
