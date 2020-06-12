import logging
import os
import os.path
import time
import traceback

from pypylon import pylon
import cv2

from idoc.server.core.base import Root
from idoc.server.io.cameras import AdaptorCamera
from idoc.server.utils.cameras import reset_pylon_camera

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



class PylonCamera(AdaptorCamera, Root):
    r"""
    Drive a Basler camera using pypylon.
    """

    def __init__(self, *args, timeout=5000, video_path=None, wrap=False, **kwargs):

        # TODO Put this stuff in the config
        self._max_failed_count = 10
        self._timeout = timeout
        self._video_path = video_path
        self._wrap = wrap
        super().__init__(*args, **kwargs)

    def is_last_frame(self):
        return False

    def _time_stamp(self):
        now = time.time()
        return now - self._start_time

    def is_opened(self):
        return self.camera.IsOpen()

    def _next_image(self):

        failed_count = 0
        # this while loop is designed to try several times,
        # not to be run continuosly
        # i.e. in normal conditions, it should be broken every time
        # the continously running loop is implemented BaseCamera.__iter__

        # import ipdb; ipdb.set_trace()

        while self.camera.IsGrabbing():

            # logger.warning('Input framerate is %s', str(self.framerate))

            grab = self._grab()
            if not grab.GrabSucceeded():
                logger.debug("Pylon could not fetch next frame. Trial no %d", failed_count)
                failed_count += 1
            else:
                break

            if failed_count == self._max_failed_count:
                template = "Tried reading next frame %d times and none worked. Exiting."
                message = template % self._max_failed_count
                logger.warning(message)
                self.close()

        # Access the image data.
        img = grab.Array
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        self._validate(img)
        return img

    def open(self):

        try:
            super().open()
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            # Print the model name of the camera.
            logger.info("Using device %s", self.camera.GetDeviceInfo().GetModelName())
            # self.camera.StartGrabbingMax(100) # if we want to limit the number of frames
            self.camera.MaxNumBuffer = 5
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            grab_result = self.camera.RetrieveResult(self._timeout, pylon.TimeoutHandling_ThrowException)
            image = grab_result.Array
            # import ipdb; ipdb.set_trace()
            logger.info("Pylon camera loaded successfully")
            logger.info("Resolution of incoming frames: %dx%d", image.shape[1], image.shape[0])

        except Exception as error:
            logger.error(error)
            logger.error(traceback.print_exc())
            self.reset()


    # called by BaseCamera.__exit__()
    def close(self):
        super().close()
        self.camera.Close()


    def restart(self):
        r"""
        Attempt to restart a Basler camera
        """
        reset_pylon_camera()


    def _grab(self):
        try:
            #import ipdb; ipdb.set_trace()
            grab_result = self.camera.RetrieveResult(self._timeout, pylon.TimeoutHandling_ThrowException)
            return grab_result

        # TODO Use right exception
        except Exception as error:  # pylint: disable=broad-except
            logger.warning("Error in _grab method")
            logger.warning(traceback.print_exc())
            logger.warning(error)
            return

    @property
    def framerate(self):
        return self._settings["framerate"]

    @framerate.getter
    def framerate(self):
        self._settings["framerate"] = self.camera.AcquisitionFrameRateAbs.GetValue()
        return self._settings["framerate"]

    @framerate.setter
    def framerate(self, framerate):
        # logger.info("Setting framerate to %s", str(framerate))
        try:
            self.camera.AcquisitionFrameRateAbs.SetValue(framerate)
        except Exception as error:
            logger.warning(error)
            logger.warning(traceback.print_exc())
        self._settings["framerate"] = framerate

    @property
    def exposure_time(self):
        return self._settings["exposure_time"]

    @exposure_time.getter
    def exposure_time(self):
        self._settings["exposure_time"] = self.camera.ExposureTimeAbs.GetValue()
        return self._settings["exposure_time"]

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        # logger.info("Setting exposure time to %3.f", exposure_time)
        try:
            self.camera.ExposureTimeAbs.SetValue(exposure_time)
        except Exception as error:
            logger.warning(error)
            logger.warning(traceback.print_exc())

        self._settings["exposure_time"] = exposure_time

    @property
    def resolution(self):
        r"""
        Convenience function to return resolution of camera.
        Resolution = (number_horizontal_pixels, number_vertical_pixels)
        """
        self._settings["resolution"] = (self.camera.Width.GetValue(), self.camera.Height.GetValue())
        return self._settings["resolution"]

    @resolution.setter
    def resolution(self, resolution):
        pass

    @property
    def shape(self):
        r"""
        Convenience function to return shape of camera
        Shape = (number_vertical_pixels, number_horizontal_pixels, number_channels)
        """
        # TODO Return number of channels!
        return (self.camera.Height.GetValue(), self.camera.Width.GetValue(), 1)
