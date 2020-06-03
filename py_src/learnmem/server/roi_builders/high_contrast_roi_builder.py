__author__ = 'antonio'

import logging

import cv2
import numpy as np

from learnmem.server.core.base import Settings, Root
from learnmem.server.roi_builders.roi_builders import BaseROIBuilder
from learnmem.server.core.roi import ROI
from learnmem.server.utils.debug import EthoscopeException

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
        self._min_width = 150
        self._max_width = 600
        self._min_height = 15
        self._max_height = 60
        self._min_thresh = 100
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
            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            if len(contours) == self._nrows * self._ncols:
                return contours

        # cv2.imwrite(os.path.join(os.environ["HOME"], 'failed_roi_builder_binary.png'), bin_orig)
        raise EthoscopeException

    @staticmethod
    def _find_center(contour):
        r"""
        Return the center of the bounding box of the contour.
        """
        bounding_box = cv2.boundingRect(contour)
        xy, wh = bounding_box

        width = np.max(wh)
        height = np.min(wh)
        x, y = xy
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

    def _rois_from_img(self, img, input=None):
        """
        Return a list of ROIS given a raw input frame.
        """

        rois = []

        if not isinstance(input, np.ndarray):
            img = self.fetch_frames(input)

        binary_img = self._threshold(img)[:, :, 0]

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

            rois.append(ROI(contour, idx=idx+1, side=side))

        return rois

    def _get_roi_score_map(self, img, threshold_value):

        # start a score_map set to 0 everywhere
        score_map = np.zeros((img.shape[0], img.shape[1], 2), dtype=np.uint8)

        # perform binary thresholding
        thresh = cv2.threshold(img, threshold_value, 255, cv2.THRESH_BINARY)[1]

        # morphological operations to denoise
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((5, 5)), iterations=3)

        # pad with only 1 pixel to avoid segmented regions touching the wall
        padded = cv2.copyMakeBorder(morph, 1, 1, 1, 1, cv2.BORDER_CONSTANT)

        # get edges
        edged = cv2.Canny(padded, 50, 100)

        if CV_VERSION == 3:
            _, contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


        # go through each contour and validate it
        for contour in contours:
            epsilon = 0.001 * cv2.arcLength(contour, True)
            approx_contour = cv2.approxPolyDP(contour, epsilon, True)
            polygon = cv2.boundingRect(approx_contour)

            _, _, w, h = polygon

            width = max([w, h])
            height = min([w, h])

            if self._min_width < width < self._max_width and self._min_height < height < self._max_height:
                contour = self._polygon2contour(polygon)
                cv2.drawContours(score_map, [contour], -1, (255, 0), -1)

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
        placeholder = np.zeros(image.shape[:2], dtype=np.uint8)
        blur = cv2.bilateralFilter(img, 10, 150, 150)

        for threshold_value in range(self._min_thresh, self._max_thresh, self._inter_thresh):
            # print(np.unique(bin, return_counts=True))
            score_map = self._get_roi_score_map(blur, threshold_value)
            placeholder = cv2.add(placeholder, score_map)

        # consider foreground any pixel with at least 10 matches
        binary_image = cv2.threshold(placeholder, 10, 255, cv2.THRESH_BINARY)[1]
        return binary_image
