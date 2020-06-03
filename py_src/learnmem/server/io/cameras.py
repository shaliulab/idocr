__author__ = 'antonio'

import logging
import time

from learnmem.server.core.base import Base, Root

# Tell pylint everything here is abstract classes
# pylint: disable=W0223


class BaseCamera(Base, Root):

    def __init__(self, *args, drop_each=1, max_duration=None, **kwargs):
        """
        The template class to generate and use video streams.

        :param drop_each: keep only ``1/drop_each``'th frame
        :param max_duration: stop the video stream if ``t > max_duration`` (in seconds).
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        super().__init__(*args, **kwargs)

        self._settings = {"drop_each": drop_each, "max_duration": max_duration}
        self.capture = None
        self._frame_idx = 0
        self._shape = (None, None)

    def __exit__(self):
        logging.info("Closing camera")
        self.close()

    def __iter__(self):
        """
        Iterate thought consecutive frames of this camera.

        :return: the time (in ms) and a frame (numpy array).
        :rtype: (int, :class:`~numpy.ndarray`)
        """
        at_least_one_frame = False
        while True:
            if self.is_last_frame() or not self.is_opened():
                if not at_least_one_frame:
                    raise Exception("Camera could not read the first frame")
                break
            t, out = self._next_time_image()
            if out is None:
                break
            t_ms = int(1000*t)
            at_least_one_frame = True

            if (self._frame_idx % self._settings["drop_each"]) == 0:
                yield t_ms, out

            if self._settings["max_duration"] is not None and t > self._settings["max_duration"]:
                break

    def _next_time_image(self):
        timestamp = self._time_stamp()
        image = self._next_image()
        self._frame_idx += 1
        return timestamp, image

    def is_last_frame(self):
        raise NotImplementedError

    def _next_image(self):
        raise NotImplementedError

    def _time_stamp(self):
        raise NotImplementedError

    def is_opened(self):
        raise NotImplementedError

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def restart(self):
        """
        Restarts a camera (also resets time).
        :return:
        """
        raise NotImplementedError

class AdaptorCamera(BaseCamera, Root):
    r"""
    Abstract adapter class based on the ethoscope BaseCamera
    providing camera input functionality to IDOC cameras
    """

    framerate = 0
    exposure_time = 0

    def __init__(self, framerate, exposure_time, *args, resolution=None, **kwargs):


        super().__init__(*args, **kwargs)
        self._settings.update({
            "framerate": 0, "exposure_time": 0, "resolution": (0, 0)
        })

        self.open()
        self._start_time = time.time()
        self._settings.update({
            "framerate": framerate,
            "exposure_time": exposure_time,
            "resolution": resolution,
        })


    def __str__(self):
        template = '%s @ %s FPS and exposure time %s ms'
        return template % (
            self.__class__.__name__,
            str(self.framerate).zfill(4),
            str(self.exposure_time).zfill(8)
        )

    @property
    def resolution(self):
        r"""
        Convenience function to return resolution of camera.
        Resolution = (number_horizontal_pixels, number_vertical_pixels)
        """
        return self._settings["resolution"]

    @resolution.setter
    def resolution(self):
        logging.warning("NotImplemented")
