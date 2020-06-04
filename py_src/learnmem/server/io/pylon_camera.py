import logging
import os
import os.path
import time
import traceback

from pypylon import pylon

from learnmem.server.core.base import Root
from learnmem.server.io.cameras import AdaptorCamera
from learnmem.server.utils.cameras import reset_pylon_camera

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



class PylonCamera(AdaptorCamera, Root):
    r"""
    Drive a Basler camera using pypylon.
    """

    def __init__(self, *args, timeout=5000, video_path=None, wrap=False, **kwargs):

        super().__init__(*args, **kwargs)
        # TODO Put this stuff in the config
        self._max_failed_count = 10
        self._timeout = timeout
        self._video_path = video_path
        self._wrap = wrap

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
        while self.camera.IsGrabbing():
            logger.warning("Pylon could not fetch next frame. Trial no %d", failed_count)
            grab = self._grab()
            if not grab.GrabSucceeded():
                failed_count += 1
            else:
                grab.Release()
                break

            if failed_count == self._max_failed_count:
                template = "Tried reading next frame %d times and none worked. Exiting."
                message = template % self._max_failed_count
                raise Exception(message)

        # Access the image data.
        img = grab.Array
        return img

    def open(self):

        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            # self.camera.StartGrabbingMax(numberOfImagesToGrab) # if we want to limit the number of frames
            logger.info("Pylon camera loaded successfully")

        except Exception as error:
            logging.error(traceback.print_exc())
            raise error

    # called by BaseCamera.__exit__()
    def close(self):
        self.camera.Close()


    def restart(self):
        r"""
        Attempt to restart a Basler camera
        """
        reset_pylon_camera()


    def _grab(self):
        try:
            return self.camera.RetrieveResult(self._timeout, pylon.TimeoutHandling_ThrowException)

        # TODO Use right exception
        except Exception as error:  # pylint: disable=broad-except
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
        logger.info("Setting framerate to %s", str(framerate))
        self.camera.AcquisitionFrameRateAbs.SetValue(framerate)
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
        logger.info("Setting exposure time to %3.f", exposure_time)
        self.camera.ExposureTimeAbs.SetValue(exposure_time)
        self._settings["exposure_time"] = exposure_time

    @property
    def resolution(self):
        r"""
        Convenience function to return resolution of camera.
        Resolution = (number_horizontal_pixels, number_vertical_pixels)
        """
        self._settings["resolution"] = (self.camera.Width.GetValue(), self.camera.Height.GetValue())
        return self._settings["resolution"]

    @property
    def shape(self):
        r"""
        Convenience function to return shape of camera
        Shape = (number_vertical_pixels, number_horizontal_pixels, number_channels)
        """
        # TODO Return number of channels!
        return (self.camera.Height.GetValue(), self.camera.Width.GetValue(), 1)
