__author__ = 'antonio'

import logging
import time

from idoc.server.core.base import Settings, Status, Root
from idoc.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tell pylint everything here is abstract classes
# pylint: disable=W0223


class BaseCamera(Settings, Status, Root):

    def __init__(self, *args, drop_each=1, max_duration=None, use_wall_clock=True, **kwargs):
        """
        The template class to generate and use video streams.

        :param drop_each: keep only ``1/drop_each``'th frame
        :param max_duration: stop the video stream if ``t > max_duration`` (in seconds).
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        super().__init__(*args, **kwargs)

        self._settings.update({"drop_each": drop_each})
        self.capture = None
        self._max_duration = max_duration
        self._frame_idx = 0
        self._shape = (None, None)
        self._use_wall_clock = use_wall_clock
        logger.info("Using wall clock is %r", self._use_wall_clock)

    # TODO Why are 3 params beyond self needed here?
    def __exit__(self): # pylint: disable=unexpected-special-method-signature
        logger.info("Closing camera")
        self.close()

    def __iter__(self):
        """
        Iterate thought consecutive frames of this camera.

        :return: the time (in ms) and a frame (numpy array).
        :rtype: (int, :class:`~numpy.ndarray`)
        """
        at_least_one_frame = False
        while not self.stopped:
            if self.is_last_frame() or not self.is_opened():
                if not at_least_one_frame:
                    raise Exception("Camera could not read the first frame")
                break
            time_s, out = self._next_time_image()
            if out is None:
                break
            t_ms = int(1000 * time_s)
            at_least_one_frame = True

            # print("self._settings")
            # print(self._settings)

            if (self._frame_idx % self._settings["drop_each"]) == 0:
                logger.debug("Time: %s, Framerate: %s", t_ms, self.framerate)
                yield t_ms, out

            if self._max_duration is not None and t_ms > self._max_duration * 1000:
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
        # super().start()
        raise NotImplementedError

    def close(self):
        super().stop()

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

    def __init__(self, *args, framerate=None, exposure_time=None, resolution=None, **kwargs):


        super().__init__(*args, **kwargs)
        self.open()
        self._start_time = time.time()
        self._settings.update({
            "framerate": framerate or self._config.content['io']['camera']['kwargs']['framerate'],
            "exposure_time": exposure_time or self._config.content['io']['camera']['kwargs']['exposure_time'],
            "resolution": resolution or self._config.content['io']['camera']['kwargs']['resolution'],
            "video_path": None
        })


    def __str__(self):
        template = '%s @ %s FPS and exposure time %s ms'
        return template % (
            self.__class__.__name__,
            str(self.framerate).zfill(4),
            str(self.exposure_time).zfill(8)
        )

    def open(self):
        super().run()

    def close(self):
        super().stop()

    @staticmethod
    def _validate(img):
        if img is not None:
            if len(img.shape) != 3:
                raise IDOCException("camera output is not 3D")


    @property
    def resolution(self):
        r"""
        Convenience function to return resolution of camera.
        Resolution = (number_horizontal_pixels, number_vertical_pixels)
        """
        return self._settings["resolution"]

    @resolution.setter
    def resolution(self):
        logger.warning("NotImplemented")
