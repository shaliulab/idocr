__author__ = 'antonio'

import logging

import cv2
import numpy as np

from idoc.server.core.base import Settings, Root
from idoc.server.roi_builders.roi_builders import BaseROIBuilder
from idoc.server.core.roi import ROI
from idoc.debug import EthoscopeException

try:
    CV_VERSION = int(cv2.__version__.split(".")[0])
except:
    CV_VERSION = 2

try:
    from cv2.cv import CV_CHAIN_APPROX_SIMPLE as CHAIN_APPROX_SIMPLE
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import CHAIN_APPROX_SIMPLE
    from cv2 import LINE_AA

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HighContrastROIBuilder(BaseROIBuilder, Settings, Root):

    _adaptive_med_rad = 0.05
    _expected__min_target_dist = 10 # the minimal distance between two targets, in 'target diameter'
    _description = {
        "overview": """
        A flexible ROI builder that allows users to select parameters for the ROI layout.
        Lengths are relative to the distance between the two bottom targets (width)
        """
    }

    def __init__(self, *args, nrows=10, ncols=2, **kwargs):
        """
        This roi builder takes advantage of the hight contrast
        between the ROIs and the background when illuminated with IR light.
        It is particularly powerful when the ROI is the only area with light.

        :param nrows: The number of rows in the grid.
        :type nrows: int
        :param ncols: The number of columns.
        :type ncols: int
        """

        self._nrows = nrows
        self._ncols = ncols
        self._min_area = 1500
        self._max_area = 2500

        self._min_thresh = 0
        self._max_thresh = 255
        self._inter_thresh = 4

        super().__init__(*args, **kwargs)


    def _find_contours(self, binary_image):
        r"""
        Receive a binary image and return a list of contours
        """

        while np.count_nonzero(binary_image) > 0:

            # bin = cv2.morphologyEx(bin, cv2.MORPH_TOPHAT, (9, 9))
            binary_image = cv2.erode(binary_image, np.ones((1, 10)))

            # cv2.imshow('binary', binary_image)
            # cv2.waitKey(0)

            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            if len(contours) == self._nrows * self._ncols:
                return contours

        # cv2.imwrite(os.path.join(os.environ["HOME"], 'failed_roi_builder_binary.png'), bin_orig)
        raise EthoscopeException("")

    @staticmethod
    def _find_center(contour):
        r"""
        Return the center of the bounding box of the contour.
        """
        x, y, w, h = cv2.boundingRect(contour)
        width = np.max([w, h])
        height = np.min([w, h])
        center = (x + width // 2, y + height // 2)
        return center

    @staticmethod
    def _find_quadrant(shape, center):
        r"""
        Return a str of length 2 encoding wich quadrant
        the center is in:
        tl, tr, br, bl
        """
        quadrant = ['b', 'r']

        left = center[0] < (shape[1] / 2)
        top = center[1] > (shape[0] / 2)
        if top:
            quadrant[0] = 't'
        if left:
            quadrant[1] = 'l'

        return ''.join(quadrant)

    @staticmethod
    def _polygon2contour(polygon):

        return [
            (polygon[0], polygon[1]),
            (polygon[0]+polygon[2], polygon[1]),
            (polygon[0]+polygon[2], polygon[1]+polygon[3]),
            (polygon[0], polygon[1]+polygon[3])
        ]

    def _rois_from_img(self, img):
        """
        Return a list of ROIS given a raw input frame.
        """

        rois = []

        if img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        binary_img = self._threshold(gray)

        try:
            contours = self._find_contours(binary_img)
        except EthoscopeException:
            raise EthoscopeException("I could not find all ROIs. Please try again or change the lighting conditions.", binary_img)

        for idx, contour in enumerate(contours):
            center = self._find_center(contour)
            quadrant = self._find_quadrant(img.shape, center)
            side = 'right'
            if quadrant[1] == 'l':
                side = 'left'

            roi = ROI(contour, idx=idx+1, side=side)
            rois.append(roi)
            logger.debug("x/200 for roi %d: %d", roi.idx, roi.get_feature_dict()['x'] // 200)


        rois = sorted(rois, key=lambda roi: (roi.get_feature_dict()['x'] // 200, roi.get_feature_dict()['y']))
        for idx, roi in enumerate(rois):
            roi._idx = idx + 1

        return rois

    def _get_roi_score_map(self, img, threshold_value):

        # start a score_map set to 0 everywhere
        score_map = np.zeros(img.shape, dtype=np.uint8)

        # perform binary thresholding
        thresh = cv2.threshold(img, threshold_value, 255, cv2.THRESH_BINARY)[1]

        # cv2.imshow('thresh', thresh)
        # cv2.waitKey(0)

        # morphological operations to denoise
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((5, 5)), iterations=5)

        # pad with only 1 pixel to avoid segmented regions touching the wall
        padded = cv2.copyMakeBorder(morph, 1, 1, 1, 1, cv2.BORDER_CONSTANT)

        # get edges
        edged = cv2.Canny(padded, 50, 100)

        # cv2.imshow('edged', edged)
        # cv2.waitKey(0)

        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


        # go through each contour and validate it
        for contour in contours:
            epsilon = 0.001 * cv2.arcLength(contour, True)
            approx_contour = cv2.approxPolyDP(contour, epsilon, True)
            area = cv2.contourArea(approx_contour)

            if self._min_area < area < self._max_area:
                logger.debug(area)
                cv2.drawContours(score_map, [approx_contour], -1, 1, -1)

        return score_map

    def _threshold(self, img):
        r"""
        ROIs are segmented by:
        * BILFILT
        * THRESH LOOP
           1. MORPH X 5
           2. SURROUND BY BLACK TO AVOID WALL EFFECT
           3. CANNY (edge detection)
           4. FIND CONTS
           5. CONT LOOP
           6. APPROX CONTOUR
           7. MINAREARECT
           8. IF WIDTH AND HEIGHT ARE OK
           9. UPDATE SCORE MAP
        """
        image = img.copy()

        # store the addition of all the score_map
        # computed on each iteration
        placeholder = np.zeros(image.shape, dtype=np.uint8)
        blur = cv2.bilateralFilter(img, 10, 150, 150)

        for threshold_value in range(self._min_thresh, self._max_thresh, self._inter_thresh):
            # print(np.unique(bin, return_counts=True))
            score_map = self._get_roi_score_map(blur, threshold_value)
            placeholder = cv2.add(placeholder, score_map)

            # cv2.imshow('placeholder', placeholder)
            # cv2.waitKey(0)

        # consider foreground any pixel with at least 10 matches
        binary_image = cv2.threshold(placeholder, 5, 255, cv2.THRESH_BINARY)[1]
        return binary_image
