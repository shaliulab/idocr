import logging
import os
import sys

from pypylon import pylon
from pypylon import genicam
import cv2
import coloredlogs

from frets_utils import setup_logging
from decorators import export 

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

setup_logging()

log = logging.getLogger(__name__)

@export
class PylonStream():
    def __init__(self, video=None):
        log.info("Starting pylon camera!")

        ## TODO
        ## Check camera is visible!
        try:
            cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        except genicam._genicam.RuntimeException:
            os.system("sudo bash {}/utils/open_camera.sh".format(ROOT_DIR))
            try:
                cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            except genicam._genicam.RuntimeException:
                log.exception('Camera could not be loaded. Looks like the computer cannot access it')
                sys.exit(1)
            

        # Print the model name of the camera.
        device_info = cap.GetDeviceInfo()
        log.info("Using device {}".format(device_info.GetModelName()))
        log.info(device_info.GetFullName())
        # print(device_info.GetPropertyAvailable())
        
    
        # The parameter MaxNumBuffer can be used to control the count of buffers
        # allocated for grabbing. The default value of this parameter is 10.
        cap.MaxNumBuffer = 5

   
        # Start the grabbing of c_countOfImagesToGrab images.
        # The camera device is parameterized with a default configuration which
        # sets up free-running continuous acquisition.
        cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        #width = cap.Width.GetValue() // 3
        #offset_x = width
        #cap.OffsetX.Max = 1000
        #cap.OffsetX = offset_x
        #cap.Width = width
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

    def set_fps(self, fps):
        self.stream.AcquisitionFrameRateAbs.SetValue(fps)

    def read_frame(self):
        # Wait for an image and then retrieve it. A timeout of 5000 ms is used.
        log.info('Reading frame')
        grabResult = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        self.grabResult = grabResult
        # Image grabbed successfully?
        ret = False
        count = 1
        ret = grabResult.GrabSucceeded()
        while not ret and count < 10:
            count += 1
            log.warning("Pylon could not fetch next frame. Trial no {}".format(count))
            grabResult = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            self.grabResult = grabResult
            ret = grabResult.GrabSucceeded()
        if count == 10:
            log.error("Tried reading next frame 10 times and none worked. Exiting :(")
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
class StandardStream():

    def __init__(self, video=None):
        if video == 0:
            log.info("Capturing stream!")
            self.cap = cv2.VideoCapture(video)
        elif video != 0:
            log.info("Opening {}!".format(video))
            self.cap = cv2.VideoCapture(video.__str__())

    def get_fps(self):
        fps = self.cap.get(5)
        if fps == 0:
            return 2
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
        if self.get_fps() != fps:
            log.info("Settting fps to {}".format(fps))
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

streams_dict = {"pylon": PylonStream, "opencv": StandardStream}

