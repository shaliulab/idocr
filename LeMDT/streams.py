import logging
from pathlib import Path
import os
import sys
import time

from pypylon import pylon
from pypylon import genicam
import cv2
import coloredlogs
import numpy as np
import psutil

from .decorators import export 
from . import UTILS_DIR


class StandardStream():

    def __init__(self, tracker):
        self.tracker = tracker

    def get_width(self):
        raise Exception
    
    def get_height(self):
        raise Exception

    def get_dimensions(self):
        return self.get_width(), self.get_height()


@export
class PylonStream(StandardStream):
    def __init__(self, tracker, video=None):

        super(PylonStream, self).__init__(tracker)
        self.log = tracker.interface.getLogger(__name__)
        self.log.info("Attempting to open pylon camera")

        ## TODO
        ## Check camera is visible!
        try:
            cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        except genicam._genicam.RuntimeException as e:
            self.log.warning(e)
            self.log.warning('Running open_camera.sh')
            script_path = Path(UTILS_DIR, 'open_camera.sh').__str__() 
            os.system("bash {}".format(script_path))
            time.sleep(5)
            try:
                cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            except genicam._genicam.RuntimeException as e:
                self.log.exception(e)
                self.log.error('Camera could not be opened. Is the switch off?!')
                sys.exit(1)

        except genicam._genicam.AccessException as e:
            self.log.warning('An exception has occurred. Camera could not be opened')
            self.log.critical(e)
            self.status = 0
            return 0
        finally:
            pass

        # Print the model name of the camera.
        device_info = cap.GetDeviceInfo()
        self.log.info("Using device {}".format(device_info.GetModelName()))
        self.log.info(device_info.GetFullName())
        # print(device_info.GetPropertyAvailable())
        
    
        # The parameter MaxNumBuffer can be used to control the count of buffers
        # allocated for grabbing. The default value of this parameter is 10.
        cap.MaxNumBuffer = 5

   
        # Start the grabbing of c_countOfImagesToGrab images.
        # The camera device is parameterized with a default configuration which
        # sets up free-running continuous acquisition.
        try:
            cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            process = [p for p in psutil.process_iter() if 'Pylon' in p.name()]
            if len(process) != 0:
                self.log.warning('A running instance of PylonViewerApp was detected')
                self.log.warning('Closing as Python will not be able to access the camera then')
                [p.kill() for p in process]
                time.sleep(3)
                cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            else:             
                self.log.error('Camera could not grab frames. This is likely to be caused by the camera being already in use')
                self.log.error('This can happen if the program has recently been closed')
                self.log.error('Try again in a few seconds')
                self.log.debug(e)


        #width = cap.Width.GetValue() // 3
        #offset_x = width
        #cap.OffsetX.Max = 1000
        #cap.OffsetX = offset_x
        #cap.Width = width
        self.cap = cap

        self.log.info("Pylon camera loaded successfully")



    def get_fps(self):
        fps = self.cap.AcquisitionFrameRateAbs.GetValue()
        return fps

    def get_width(self):
        width = self.cap.Width.GetValue()
        return width

    def get_height(self):
        height = self.cap.Height.GetValue()
        return height

    def set_fps(self, fps):
        self.log.info("Setting fps to {}".format(fps))
        self.cap.AcquisitionFrameRateAbs.SetValue(fps)


    def set_acquisition_time(self, at):
        self.log.info("Setting acquisition time to {}".format(at))
        self.cap.ExposureTimeAbs.SetValue(at)

    def get_acquisition_time(self, at):
        self.log.info("Acquisition time set to: {}".format(self.cap.ExposureTimeAbs.GetValue(at)))


    def retrieve_result(self):
        while True:
            try:
                grabResult = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                break
            except Exception as e:
                self.log.exception(e)

        self.grabResult = grabResult        
        return grabResult


    def read_frame(self):
        # Wait for an image and then retrieve it. A timeout of 5000 ms is used.
        self.log.debug('Reading frame')

        grabResult = self.retrieve_result()      
        
        # Image grabbed successfully?
        ret = False
        count = 1
        ret = grabResult.GrabSucceeded()
        while not ret and count < 10:
            count += 1
            self.log.warning("Pylon could not fetch next frame. Trial no {}".format(count))
            grabResult = self.retrieve_result()

            ret = grabResult.GrabSucceeded()
        if count == 10:
            self.log.error("Tried reading next frame 10 times and none worked. Exiting :(")
            sys.exit(1)
        #print(ret)
        if ret:
            # Access the image data.
            #print("SizeX: ", grabResult.Width)
            #print("SizeY: ", grabResult.Height)
            img = grabResult.Array
            return ret, img
        return False, None

    def release(self):
        self.grabResult.Release()

@export
class WebCamStream(StandardStream):

    def __init__(self, tracker, video=None):

        super(WebCamStream, self).__init__(tracker)

        self.log = tracker.interface.getLogger(__name__)

        if video == 0:
            self.log.info("Attempting to open webcam")
            self.cap = cv2.VideoCapture(video)
            self.log.info("Webcam opened successfully")

        elif video != 0:
            self.log.info("Opening {}!".format(video))
            self.cap = cv2.VideoCapture(video.__str__())
        


    def get_fps(self):
        fps = self.cap.get(5)
        return fps

#    def get_time_position(self, frame_count):
#        t = frame_count / self.get_fps()
#        return t

    def get_width(self):
        width = int(self.cap.get(3))
        return width

    def get_height(self):
        height = int(self.cap.get(4))
        return height 

    def set_fps(self, fps):
        import ipdb
        ipdb.set_trace()

        if self.get_fps() != fps:
            self.log.info("Setting fps to {}".format(fps))
            self.cap.set(5, fps)

    def set_acquisition_time(self, at):
        self.log.warning("Change of acquisition time not implemented")
        pass

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

STREAMS = {"pylon": PylonStream, "webcam": WebCamStream}
