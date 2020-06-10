__author__ = 'quentin'

import logging
import itertools
import pickle
import os


import numpy as np
import cv2


from idoc.server.roi_builders.roi_builders import BaseROIBuilder
from idoc.server.core.roi import ROI
from idoc.debug import IDOCException, EthoscopeException
from idoc.server.roi_builders.helpers import find_quadrant

try:
    CV_VERSION = int(cv2.__version__.split(".")[0]) # pylint: disable=no-member
except:
    CV_VERSION = 2

try:
    from cv2.cv import CV_CHAIN_APPROX_SIMPLE as CHAIN_APPROX_SIMPLE
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import CHAIN_APPROX_SIMPLE
    from cv2 import LINE_AA

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class TargetGridROIBuilder(BaseROIBuilder):

    _adaptive_med_rad = 0.10
    _expected_min_target_dist = 200 # the minimal distance between two targets, in 'target diameter'
    _n_rows = 10
    _n_cols = 2
    _top_margin = 0
    _bottom_margin = None
    _left_margin = 0
    _right_margin = None
    _horizontal_fill = 1
    _vertical_fill = None
    _inside_pad = 0.0
    _outside_pad = 0.0
    _reverse = False
    # MAGIC NUMBERS
    _max_non_zero = 0.7
    _min_area_perimeter_ratio = 0.8
    _min_target_area = 400
    _max_target_area = 800
    _min_area_ratio = 1
    _max_area_ratio = 1.5
    # END

    _target_coord_file = "/etc/target_coordinates.conf"
    _rois_pickle_file = "rois.pickle"

    _description = {"overview": "A flexible ROI builder that allows users to select parameters for the ROI layout."
                               "Lengths are relative to the distance between the two bottom targets (width)",
                    "arguments": [
                        {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_cols", "description": "The number of columns", "default":1},
                        {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_rows", "description": "The number of rows", "default":1},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "top_margin", "description": "The vertical distance between the middle of the top ROIs and the middle of the top target.", "default":0.0},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "bottom_margin", "description": "Same as top_margin, but for the bottom.", "default":0.0},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "right_margin", "description": "Same as top_margin, but for the right.", "default":0.0},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "left_margin", "description": "Same as top_margin, but for the left.", "default":0.0},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "horizontal_fill", "description": "The proportion of the grid space used by the roi, horizontally.", "default":0.90},
                        {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "vertical_fill", "description": "Same as horizontal_margin, but vertically.", "default":0.90}
                    ]}

    def __init__(self, *args, n_rows=1, n_cols=1, top_margin=0, bottom_margin=0,
                 left_margin=0, right_margin=0, horizontal_fill=.9, vertical_fill=.9, inside_pad=.0, outside_pad=.0, **kwargs):
        """
        This roi builder uses three black circles drawn on the arena (targets) to align a grid layout:

        IMAGE HERE

        :param n_rows: The number of rows in the grid.
        :type n_rows: int
        :param n_cols: The number of columns.
        :type n_cols: int
        :param top_margin: The vertical distance between the middle of the top ROIs and the middle of the top target
        :type top_margin: float
        :param bottom_margin: same as top_margin, but for the bottom.
        :type bottom_margin: float
        :param left_margin: same as top_margin, but for the left side.
        :type left_margin: float
        :param right_margin: same as top_margin, but for the right side.
        :type right_margin: float
        :param horizontal_fill: The proportion of the grid space user by the roi, horizontally (between 0 and 1).
        :type horizontal_fill: float
        :param vertical_fill: same as vertical_fill, but horizontally.
        :type vertical_fill: float
        """

        self._n_rows = n_rows
        self._n_cols = n_cols
        self._top_margin =  top_margin
        self._bottom_margin = bottom_margin
        self._left_margin = left_margin
        self._right_margin = right_margin
        self._horizontal_fill = horizontal_fill
        self._vertical_fill = vertical_fill
        self._inside_pad = inside_pad
        self._outside_pad = outside_pad
        self._sorted_src_pts = [None, ] * 3
        self._img = None

        if 'target_coordinates_file' in kwargs.keys():
            self._target_coord_file = kwargs.pop('target_coordinates_file')

        if 'rois_pickle_file' in kwargs.keys():
            self._rois_pickle_file = kwargs.pop('rois_pickle_file')

        super().__init__(*args, **kwargs)

    def _sort_src_pts(self, src_points):
        """
        Sort the three dots / targets on the arena by their position
        Maximum distance is between A and C
        The point not having the most distance with other points is thus B
        C is the one with the highest distance to B
        A is the other one (with the lowest distance)

        """
        a, b, c = src_points

        pairs = [(a, b), (b, c), (a, c)]

        dists = [self._points_distance(*p) for p in pairs]

        for d in dists:
            logger.info(d)
            if d < self._expected_min_target_dist:
                raise EthoscopeException(
                                    """
                                    The detected targets are too close.
                                    If you think this is correct, please decrease the value of _expected_min_target_dist
                                    to something that fits your setup. It is set to %i
                                    """ % self._expected_min_target_dist
                                    )
        # that is the AC pair
        hypo_vertices = pairs[np.argmax(dists)]

        # this is B : the only point not in (a,c)
        for sp in src_points:
            if not sp in hypo_vertices:
                break
        sorted_b = sp # pylint: disable=undefined-loop-variable

        dist = 0
        for sp in src_points:
            if sorted_b is sp:
                continue
            # b-c is the largest distance, so we can infer what point is c
            if self._points_distance(sp, sorted_b) > dist:
                dist = self._points_distance(sp, sorted_b)
                sorted_c = sp

        # the remaining point is a
        sorted_a = [sp for sp in src_points if not sp is sorted_b and not sp is sorted_c][0]
        sorted_src_pts = np.array([sorted_a, sorted_b, sorted_c], dtype=np.float32)
        if self._reverse:
            sorted_src_pts = sorted_src_pts[::-1]

        self._sorted_src_pts = sorted_src_pts
        logger.debug(sorted_src_pts)

        return sorted_src_pts

    def _find_blobs(self, image, scoring_fun=None):

        if scoring_fun is None:
            scoring_fun = self._score_targets

        #grey= cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        grey = image
        radius = int(self._adaptive_med_rad * image.shape[1])
        if radius % 2 == 0:
            radius += 1

        # cv2.imhow('grey', grey)
        # cv2.waitKey(0)

        med = np.median(grey)
        if med > 20:
            scale = 255 / (med)
            cv2.multiply(grey, scale, dst=grey)
            binary = np.copy(grey)
        else:
            binary = np.copy(grey)

        # cv2.imshow('bin', bin)
        # cv2.waitKey(0)
        score_map = np.zeros_like(binary)
        for threshold in range(0, 255, 5):

            cv2.threshold(grey, threshold, 255, cv2.THRESH_BINARY, binary)
            # cv2.imwrite('/root/find_blobs_threshold_%d.png' % threshold, binary)

            if np.count_nonzero(binary) > self._max_non_zero * image.shape[0] * image.shape[1]:
                continue
            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            binary.fill(0)
            for contour in contours:
                score = scoring_fun(contour)
                if score > 0:
                    cv2.drawContours(binary, [contour], 0, score, -1)

            cv2.add(binary, score_map, score_map)
            # cv2.imwrite('/root/find_blobs_score_map_%d.png' % threshold, binary)

        return score_map

    def _find_blobs_new(self, image, scoring_fun=None):

        grey = image
        if scoring_fun is None:
            scoring_fun = self._score_circles

        # radius of dots is 0.1 * width of image
        # units?
        rad = int(self._adaptive_med_rad * grey.shape[1])
        # make sure it is an odd
        if rad % 2 == 0:
            rad += 1

        # make median intensity 255
        med = np.median(grey)
        scale = 255/(med)
        cv2.multiply(grey, scale, dst=grey)
        binary = np.copy(grey)
        score_map = np.zeros_like(binary)
        # grey_orig = grey.copy()

        for threshold in range(0, 255, 5):
            cv2.threshold(grey, threshold, 255, cv2.THRESH_BINARY_INV, binary)

            # cv2.imwrite('/root/find_blobs_new_threshold_%d.png' % threshold, binary)

            non_zero_pixels = np.count_nonzero(binary)

            # if this threshold operation leaves
            # more than 70% white pixels, continue
            # until loop is over
            if non_zero_pixels > self._max_non_zero * grey.shape[0] * grey.shape[1]:
                continue

            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            foreground_model = cv2.drawContours(grey.copy(), contours, -1, 255, -1)
            _, foreground_model = cv2.threshold(foreground_model, 254, 255, cv2.THRESH_BINARY)
            foreground_model = cv2.morphologyEx(foreground_model, cv2.MORPH_CLOSE, kernel=np.ones((3, 3)), iterations=1)

            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            binary.fill(0)

            for contour in contours:
                score = scoring_fun(contour)
                if score > 0:
                    cv2.drawContours(binary, [contour], 0, score, -1)

            score_map = cv2.add(binary, score_map, score_map)
            # cv2.imwrite('/root/find_blobs_new_score_map_%d.png' % threshold, score_map)


        return score_map

    @staticmethod
    def _make_grid(
            n_col, n_row,
            top_margin=0.0, bottom_margin=0.0,
            left_margin=0.0, right_margin=0.0,
            horizontal_fill=1.0, vertical_fill=1.0,
            inside_pad=0.0, outside_pad=0.0
        ):

        y_positions = (np.arange(n_row) * 2.0 + 1) * (1 - top_margin - bottom_margin) / (2 * n_row) + top_margin
        x_positions = (np.arange(n_col) * 2.0 + 1) * (1 - left_margin - right_margin) / (2 * n_col) + left_margin
        all_centres = [np.array([x, y]) for x, y in itertools.product(x_positions, y_positions)]

        padded_centres = []
        for center in all_centres:
            left, top = find_quadrant((1, 1), center)
            if left:
                center[0] -= inside_pad
                center[0] += outside_pad
            else:
                center[0] += inside_pad
                center[0] -= outside_pad

            padded_centres.append(center)
        all_centres = padded_centres

        sign_mat = np.array([
            [-1, -1],
            [+1, -1],
            [+1, +1],
            [-1, +1]

        ])
        xy_size_vec = np.array([horizontal_fill/float(n_col), vertical_fill/float(n_row)]) / 2.0
        rectangles = [sign_mat *xy_size_vec + c for c in all_centres]
        return rectangles


    @staticmethod
    def _points_distance(pt1, pt2):
        x1 , y1  = pt1
        x2 , y2  = pt2
        return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def _score_targets(self, contour):

        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            return 0
        circle = 4 * np.pi * area / perimeter ** 2

        if circle < self._min_area_perimeter_ratio:
            return 0

        return 1

    def _score_circles(self, contour):
        """
        Score the target quality by checking
        * its area is within limits
        * the ratio of the area of the minimal enclosing circle and its area is within limits
        """

        area = cv2.contourArea(contour)

        if not self._min_target_area > area > self._max_target_area:
            return 0

        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        # if area was zero the functionw would have already returned
        ratio = np.pi * radius ** 2 / area
        # print(ratio)

        if self._min_area_ratio < ratio < self._max_area_ratio:
            return 1

        return 0

    def _find_target_coordinates(self, image, blob_function):
        """
        :param image: A single channel image (2D)
        :type image: np.array
        """

        if len(image.shape) != 2:
            raise IDOCException("find_target_coordinates: image is not 2D")

        score_map = blob_function(image)

        # cv2.imshow('blob_score_map', score_map)
        # cv2.waitKey(0)

        binary = np.zeros_like(score_map)

        # as soon as we have three objects, we stop
        contours = []
        for threshold in range(0, 255, 1):

            cv2.threshold(score_map, threshold, 255, cv2.THRESH_BINARY, binary)

            # cv2.imshow('threshold', binary)
            # cv2.waitKey(0)

            if CV_VERSION == 3:
                _, contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            if len(contours) < 3:
                raise EthoscopeException("There should be three targets. Only %i objects have been found" % (len(contours)), image)
            if len(contours) == 3:
                break

        target_diams = [cv2.boundingRect(contour)[2] for contour in contours]

        mean_diam = np.mean(target_diams)
        mean_sd = np.std(target_diams)

        if mean_sd / mean_diam > 0.10:
            raise EthoscopeException(
                """
                Too much variation in the diameter of the targets.
                Something must be wrong since all target should have the same size
                """,
                image
            )

        src_points = []
        for contour in contours:
            moms = cv2.moments(contour)
            x, y = moms["m10"] / moms["m00"], moms["m01"] / moms["m00"]
            src_points.append((x, y))

        sorted_src_pts = self._sort_src_pts(src_points)

        from idoc.server.roi_builders.helpers import place_dots
        image_dots = place_dots(image.copy(), sorted_src_pts, color=0)
        cv2.imwrite("/root/image_dots.png", image_dots)

        return sorted_src_pts

    def _rois_from_img(self, image):
        """
        :param image: A 3 channel image. It can be gray, but 3 channels are needed
        :type image: np.array
        """


        self._img = image

        # Part 0: if a pickle file storing the position of the rois is provided
        # just load it and return the rois contained in it, terminating the routine
        if os.path.exists(self._rois_pickle_file):
            with open(self._rois_pickle_file, "rb") as filehandle:
                rois = pickle.load(filehandle)
            return rois

        else:
            # Part 1.A if there is no pickle file but a target_coord_file is available
            # load the sorted_src_pts from it and continue to part 2

            if os.path.exists(self._target_coord_file):
                with open(self._target_coord_file, "r") as filehandle:
                    data = filehandle.read()

                # each dot is in a newline
                data = data.split("\n")[:3]
                # each dot is made by two numbers separated by comma
                src_points = [tuple([int(f) for f in e.split(",")]) for e in data]
                sorted_src_pts = self._sort_src_pts(src_points)

            # Part 1.B no pickle file nor target_coord_file is present. Try finding where the targets are
            # calling find_target_coordinates
            else:
                try:
                    sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(self._img, cv2.COLOR_BGR2GRAY), self._find_blobs)
                except EthoscopeException as e:
                    # raise e
                    logger.warning("Fall back to find_blobs_new")
                    sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(self._img, cv2.COLOR_BGR2GRAY), self._find_blobs_new)
                except Exception as e:
                    raise e

            # Part 2 Fit a grid to the frame using the three detected targets
            # Use the grid to position the ROIs in the right place
            # and return them as a list of objects of class ROI.

            dst_points = np.array([
                (0, -1),
                (0, 0),
                (-1, 0)
            ], dtype=np.float32)

            wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)

            rectangles = self._make_grid(
                self._n_cols, self._n_rows,
                self._top_margin, self._bottom_margin,
                self._left_margin, self._right_margin,
                self._horizontal_fill, self._vertical_fill,
                self._inside_pad, self._outside_pad
            )

            shift = np.dot(wrap_mat, [1, 1, 0]) - sorted_src_pts[1] # point 1 is the ref, at 0,0
            rois = []

            for i, r in enumerate(rectangles):

                r = np.append(r, np.zeros((4, 1)), axis=1)
                mapped_rectangle = np.dot(wrap_mat, r.T).T
                mapped_rectangle -= shift
                ct = mapped_rectangle.astype(np.int32)
                cv2.drawContours(self._img, [ct.reshape((1, 4, 2))], -1, (255, 0, 0), 1, LINE_AA)
                rois.append(ROI(ct, idx=i+1))

        return rois


class FSLSleepMonitorWithTargetROIBuilder(TargetGridROIBuilder):

    _description = {"overview": "The default sleep monitor arena with ten rows of two tubes.",
                    "arguments": []}

    def __init__(self, *args, **kwargs):
        r"""
        Class to build ROIs for a two-columns, ten-rows for the sleep monitor
        (`see here <https://github.com/gilestrolab/ethoscope_hardware/tree/master/arenas/arena_10x2_shortTubes>`_).
        """
        #`sleep monitor tube holder arena <todo>`_

        super().__init__(
            *args,
            n_rows=10,
            n_cols=2,
            top_margin=6.99 / 111.00,
            bottom_margin=6.99 / 111.00,
            left_margin=-.033,
            right_margin=-.033,
            horizontal_fill=.8,
            vertical_fill=.5,
            inside_pad=0.07,
            outside_pad=0.0,
            **kwargs
        )



class IDOCROIBuilder(TargetGridROIBuilder):

    _reverse = True

    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            n_rows=10, n_cols=2,
            top_margin=1.2 / 111.00, bottom_margin=1.8 / 111.00,
            left_margin=0.033, right_margin=0.033,
            horizontal_fill=.5, vertical_fill=.40,
            inside_pad=.05, outside_pad=.0,
            **kwargs
        )
