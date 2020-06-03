import logging
import os
import os.path
import sys
import time
import traceback

import cv2
# import numpy as np
import psutil

from pypylon import pylon


from learnmem import UTILS_DIR
from learnmem.server.core.base import Base, Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StandardStream(Base, Root):

    _settings = {"framerate": None, "exposure_time": None}
    _submodules = []

    def __init__(self, *args, **kwargs):
        self._framerate = 0
        self._resolution = (0, 0)
        self._exposure_time = 0

        super().__init__(*args, **kwargs)


    @property
    def shape(self):
        return (self._resolution[1], self._resolution[0], 3)


    def release(self):
        raise NotImplementedError


    def stop(self):
        super().stop()
        self.release()



class PylonStream(StandardStream):

    def __init__(self, *args, **kwargs):

        super(PylonStream, self).__init__()
        logger.info("Attempting to open pylon camera")
        self.cap = self.connect()
        self._grab_result = None

        super().__init__(*args, **kwargs)


    def restart(self):
        r"""
        Attempt to restart a Basler camera
        """
        logger.warning('Running open_camera.sh')
        # TODO Improve connection to bash script
        script_path = os.path.join(UTILS_DIR, 'open_camera.sh')
        os.system("bash {}".format(script_path))
        time.sleep(5)

    def _connect(self):

        try:
            cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

        # TODO Use right exceptions
        except Exception: # pylint: disable=broad-except
            try:
                cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            except Exception as error:
                logging.error("Cannot connect to camera")
                logging.error(traceback.print_exc())
                raise error

        # The parameter MaxNumBuffer can be used to control the count of buffers
        # allocated for grabbing. The default value of this parameter is 10.
        cap.MaxNumBuffer = 5
        return cap

    def _trial(self, cap):
        # Start the grabbing of c_countOfImagesToGrab images.
        # The camera device is parameterized with a default configuration which
        # sets up free-running continuous exposure.
        try:
            cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        # TODO Use right exceptions
        except Exception as error:  # pylint: disable=broad-except
            process = [p for p in psutil.process_iter() if 'Pylon' in p.name()]
            if len(process) != 0:
                logger.warning('A running instance of PylonViewerApp was detected')
                logger.warning('Closing as Python will not be able to access the camera then')
                _ = [p.kill() for p in process]
                time.sleep(3)
                cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            else:
                logger.error('Camera could not grab frames. This is likely to be caused by the camera being already in use')
                logger.error('This can happen if the program has recently been closed')
                logger.error('Try again in a few seconds')
                logger.debug(error)

    def connect(self):
        cap = self._connect()
        self._trial(cap)
        logger.info("Pylon camera loaded successfully")
        return cap

    @property
    def framerate(self):
        return self._settings["framerate"]

    @framerate.getter
    def framerate(self):
        self._settings["framerate"] = self.cap.AcquisitionFrameRateAbs.GetValue()
        return self._settings["framerate"]

    @framerate.setter
    def framerate(self, framerate):
        logger.info("Setting framerate to %s", str(framerate))
        self.cap.AcquisitionFrameRateAbs.SetValue(framerate)
        self._settings["framerate"] = framerate

    @property
    def exposure_time(self):
        return self._settings["exposure_time"]

    @exposure_time.getter
    def exposure_time(self):
        self._settings["exposure_time"] = self.cap.ExposureTimeAbs.GetValue()
        return self._settings["exposure_time"]

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        logger.info("Setting exposure time to %3.f", exposure_time)
        self.cap.ExposureTimeAbs.SetValue(exposure_time)
        self._settings["exposure_time"] = exposure_time

    # @property
    # def resolution(self):
    #     return self._resolution

    @property
    def resolution(self):
        r"""
        Convenience function to return resolution of camera.
        Resolution = (number_horizontal_pixels, number_vertical_pixels)
        """
        return self.cap.Width.GetValue(), self.cap.Height.GetValue()

    @property
    def shape(self):
        r"""
        Convenience function to return shape of camera
        Shape = (number_vertical_pixels, number_horizontal_pixels, number_channels)
        """
        # TODO Return number of channels!
        return self.cap.Height.GetValue(), self.cap.Width.GetValue(), 1

    @resolution.setter
    def resolution(self, resolution):
        raise NotImplementedError



    def _read(self):
        try:
            grab_result = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        # TODO Use right exception
        except Exception as error:  # pylint: disable=broad-except
            logger.warning(traceback.print_exc())
            logger.warning(error)

        return grab_result


    def read_frame(self):
        # Wait for an image and then retrieve it. A timeout of 5000 ms is used.
        logger.debug('Reading frame')
        ret = False
        img = None

        grab_result = self._read()

        # Image grabbed successfully?
        ret = False
        count = 1
        ret = grab_result.GrabSucceeded()

        while not ret and count < 10:
            count += 1
            logger.warning("Pylon could not fetch next frame. Trial no %d", count)
            grab_result = self._read()

            ret = grab_result.GrabSucceeded()
        if count == 10:
            logger.error("Tried reading next frame 10 times and none worked. Exiting :(")
            sys.exit(1)
        #print(ret)
        if ret:
            # Access the image data.
            img = grab_result.Array
            self._grab_result = grab_result

        return ret, img


    def __str__(self):
        template = 'Pylon Camera stream @ %s and exposure time %s'
        return template % (str(self.framerate).zfill(4), str(self.exposure_time).zfill(8))

    def release(self):
        self._grab_result.Release()

class WebCamStream(StandardStream):

    def __init__(self, *args, video_path=None, **kwargs):

        self._video_path = video_path

        if self._video_path is None:
            logger.info("Attempting to open webcam")
            self.cap = cv2.VideoCapture(0)
            logger.info("Webcam opened successfully")

        elif self._video_path is not None:
            logger.info("Opening %s!", self._video_path)
            self.cap = cv2.VideoCapture(self._video_path)

        super().__init__(*args, **kwargs)

    @property
    def framerate(self):
        return self._framerate

    @property
    def resolution(self):
        return self._resolution

    @property
    def shape(self):
        return int(self.cap.get(4)), int(self.cap.get(3))

    @resolution.getter
    def resolution(self):
        # TODO Is int needed here?
        self._resolution = (int(self.cap.get(3)), int(self.cap.get(4)))
        return self._resolution

    @resolution.setter
    def resolution(self):
        raise NotImplementedError

    @property
    def exposure_time(self):
        return self._settings["exposure_time"]

    @framerate.getter
    def framerate(self):
        self._settings["framerate"] = self.cap.get(5)
        return self._settings["framerate"]

    @framerate.setter
    def framerate(self, framerate):
        self.cap.set(5, framerate)
        self._settings["framerate"] = framerate

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        raise NotImplementedError

    @exposure_time.getter
    def exposure_time(self):
        raise NotImplementedError

    def read_frame(self):
        ret, img = self.cap.read()
        return ret, img

    def release(self):
        self.cap.release()

CAMERAS = {
    "pylon": PylonStream,
    "webcam": WebCamStream
}
