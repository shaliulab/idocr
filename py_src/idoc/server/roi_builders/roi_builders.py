__author__ = 'quentin'


import logging
import traceback
import os.path

import cv2
import numpy as np

from idoc.server.core.base import DescribedObject
from idoc.server.core.roi import ROI
from idoc.debug import IDOCException, EthoscopeException

logger = logging.getLogger(__name__)

class BaseROIBuilder(DescribedObject):

    def __init__(self):
        """
        Template to design ROIBuilders. Subclasses must implement a ``_rois_from_img`` method.
        """

    @staticmethod
    def fetch_frames(input):
        # If input is an image, make a copy
        # Otherwise it is assumed to be a camera object
        # that returns frames upon iterating it.
        # Capture 5 frames and take the median intensity for each pixel
        # i.e. get an image that represents the median of 5 frames
        accum = []
        logger.debug("Fetching frames")

        if isinstance(input, np.ndarray):
            accum = np.copy(input)
        else:
            for idx, (_, frame) in enumerate(input):
                logger.debug(frame.shape)
                accum.append(frame)
                if idx == 5:
                    break

            accum = np.median(np.array(accum), 0).astype(np.uint8)

        output_path = os.path.join(os.environ["HOME"], "input.png")
        logger.info("Saving accum to %s", output_path)
        cv2.imwrite(output_path, accum)

        return accum

    def build(self, input):
        """
        Uses an input (image or camera) to build ROIs.
        When a camera is used, several frames are acquired and averaged to build a reference image.

        :param input: Either a camera object, or an image.
        :type input: :class:`~ethoscope.hardware.input.camera.BaseCamera` or :class:`~numpy.ndarray`
        :return: list(:class:`~ethoscope.core.roi.ROI`)
        """

        accum = self.fetch_frames(input)

        try:
            rois = self._rois_from_img(accum)
            img = accum

            # try:
            #     for pt in self._sorted_src_pts:
            #         roi_build_with_dots = img.copy()
            #         roi_build_with_dots = cv2.circle(roi_build_with_dots, tuple(pt), 5, (0,255,0), -1)

            #     cv2.imwrite(os.path.join(os.environ["HOME"], "roi_build_with_dots.png"), roi_build_with_dots)
            # except AttributeError as e:
            #     logging.warning(e)

        except Exception as e:
            if not isinstance(input, np.ndarray):
                del input
            logging.error(traceback.format_exc())
            raise e

        rois_w_no_value = [r for r in rois if r.value is None]

        if len(rois_w_no_value) > 0:
            rois = self._spatial_sorting(rois)
        else:
            rois = self._value_sorting(rois)
        return rois

    def _rois_from_img(self, input=None):
        raise NotImplementedError

    def _spatial_sorting(self, rois):
        '''
        returns a sorted list of ROIs objects it in ascending order based on the first value in the rectangle property
        '''
        return sorted(rois, key=lambda x: x.rectangle[0], reverse=False)

    def _value_sorting(self, rois):
        '''
        returns a sorted list of ROIs objects it in ascending order based on the .value property
        '''
        return sorted(rois, key=lambda x: x.value, reverse=False)


class DefaultROIBuilder(BaseROIBuilder):


    """
    The default ROI builder. It simply defines the entire image as a unique ROI.
    """
    _description = {"overview": "The default ROI builder. It simply defines the entire image as a unique ROI.", "arguments": []}


    def _rois_from_img(self,img):
        h, w = img.shape[0],img.shape[1]
        return[
            ROI(np.array([
                (   0,        0       ),
                (   0,        h -1    ),
                (   w - 1,    h - 1   ),
                (   w - 1,    0       )])
            , idx=1)]

