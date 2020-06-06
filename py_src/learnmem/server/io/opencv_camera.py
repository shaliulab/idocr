import logging
import time
import traceback

import cv2

from learnmem.server.core.base import Root
from learnmem.server.io.cameras import AdaptorCamera
# from learnmem.server.utils.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OpenCVCamera(AdaptorCamera, Root):

    def __init__(self, *args, video_path=None, wrap=True, **kwargs):

        self._wrap = wrap
        print("self._wrap")
        print(self._wrap)

        self._time_s = 0
        self._wrap_s = 0

        if video_path is None:
            self._video_path = 0 # capture from a webcam
        else:
            self._video_path = video_path

        super().__init__(*args, **kwargs)

    def is_last_frame(self):
        return False

    def _time_stamp(self):

        if self._video_path == 0:
            now = time.time()
            self._time_s = now - self._start_time
        else:
            self._time_s = self.camera.get(cv2.CAP_PROP_POS_MSEC) / 1000

        return self._time_s + self._wrap_s

    def is_opened(self):
        return self.camera.isOpened()

    def _next_image(self):
        ret, img = self.camera.read()
        if self._wrap and not ret:
            self._wrap_s += self._time_s
            logger.info("Rewinding video to the start")
            self.camera.set(cv2.CAP_PROP_POS_MSEC, 0)
            ret, img = self.camera.read()

        self._validate(img)
        return img

    def open(self):
        super().open()
        try:
            logger.debug('OpenCV camera opening')
            # print('OpenCV camera opening')

            self.camera = cv2.VideoCapture(self._video_path)
        except Exception as error:
            logger.error(error)
            logger.error(traceback.print_exc())
            self.reset()
        # self.camera.set(cv2.CAP_PROP_POS_MSEC, 670000)

    def close(self):
        super().close()
        self.camera.release()

    def restart(self):
        self.close()
        self.open()

    @property
    def framerate(self):
        return self._settings["framerate"]

    @framerate.getter
    def framerate(self):
        self._settings["framerate"] = self.camera.get(5)
        return self._settings["framerate"]

    @framerate.setter
    def framerate(self, framerate):
        self.camera.set(5, framerate)
        self._settings["framerate"] = framerate

    @property
    def resolution(self):
        return self._settings["resolution"]

    @resolution.getter
    def resolution(self):
        # TODO Is int needed here?
        self._settings["resolution"] = (int(self.camera.get(3)), int(self.camera.get(4)))
        return self._settings["resolution"]

    @property
    def exposure_time(self):
        return self._settings["exposure_time"]

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        self.camera.set(cv2.CAP_PROP_EXPOSURE, exposure_time)
        self._settings["exposure_time"] = exposure_time

    @exposure_time.getter
    def exposure_time(self):
        exposure_time = self.camera.get(cv2.CAP_PROP_EXPOSURE)
        self._settings["exposure_time"] = exposure_time
        return self._settings["exposure_time"]

    @property
    def shape(self):
        return int(self.camera.get(4)), int(self.camera.get(3))
