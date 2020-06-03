__author__ = 'quentin'

import logging
import itertools
import os


import cv2
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

import numpy as np

from learnmem.server.roi_builders.roi_builders import BaseROIBuilder
from learnmem.server.core.roi import ROI
from learnmem.server.utils.debug import IDOCException, EthoscopeException
from learnmem.server.roi_builders.helpers import *

logging.basicConfig(level=logging.INFO)


class TargetGridROIBuilder(BaseROIBuilder):

    _adaptive_med_rad = 0.10
    _expected_min_target_dist = 200 # the minimal distance between two targets, in 'target diameter'
    _n_rows = 10
    _n_cols = 2
    _top_margin =  0
    _bottom_margin = None
    _left_margin = 0
    _right_margin = None
    _horizontal_fill = 1
    _vertical_fill = None
    _inside_pad = 0.0
    _outside_pad = 0.0

    _target_coord_file = "/etc/target_coordinates.conf"
    _rois_pickle_file = "rois.pickle"

    _description = {"overview": "A flexible ROI builder that allows users to select parameters for the ROI layout."
                               "Lengths are relative to the distance between the two bottom targets (width)",
                    "arguments": [
                                    {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_cols", "description": "The number of columns","default":1},
                                    {"type": "number", "min": 1, "max": 16, "step":1, "name": "n_rows", "description": "The number of rows","default":1},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "top_margin", "description": "The vertical distance between the middle of the top ROIs and the middle of the top target.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "bottom_margin", "description": "Same as top_margin, but for the bottom.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "right_margin", "description": "Same as top_margin, but for the right.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "left_margin", "description": "Same as top_margin, but for the left.","default":0.0},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "horizontal_fill", "description": "The proportion of the grid space used by the roi, horizontally.","default":0.90},
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":.001, "name": "vertical_fill", "description": "Same as horizontal_margin, but vertically.","default":0.90}
                                   ]}

    def __init__(self, n_rows=1, n_cols=1, top_margin=0, bottom_margin=0,
                 left_margin=0, right_margin=0, horizontal_fill=.9, vertical_fill=.9, inside_pad=.0, outside_pad=.0, *args, **kwargs):
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
        # if self._vertical_fill is None:
        #     self._vertical_fill = self._horizontal_fill
        # if self._right_margin is None:
        #     self._right_margin = self._left_margin
        # if self._bottom_margin is None:
        #     self._bottom_margin = self._top_margin

        logging.debug(kwargs)

        if 'target_coordinates_file' in kwargs.keys():
            self._target_coord_file = kwargs.pop('target_coordinates_file')

        if 'rois_pickle_file' in kwargs.keys():
            self._rois_pickle_file = kwargs.pop('rois_pickle_file')

        super().__init__(*args, **kwargs)

    def _sort_src_pts(self, src_points):
        a, b, c = src_points

        #if debug:
        #    for pt in src_points:
        #        pt = tuple((int(e) for e in pt))
        #        thresh = cv2.circle(thresh, pt, 5, 0, -1)

        pairs = [(a,b), (b,c), (a,c)]

        dists = [self._points_distance(*p) for p in pairs]

        for d in dists:
            logging.info(d)
            if d < self._expected_min_target_dist:
                img = self._img if len(self._img.shape) == 2 else cv2.cvtColor(self._img, cv2.COLOR_BGR2GRAY)
                img = place_dots(self._img, src_points)
                output_path = os.path.join(os.environ["HOME"], "target_detection_fail_output.png")

                logging.info(f"Saving failed detection to {output_path}")
                cv2.imwrite(output_path, img)

                raise EthoscopeException(f"""The detected targets are too close.
                                         If you think this is correct, please decrease the value of _expected_min_target_dist
                                         to something that fits your setup. It is set to {self._expected_min_target_dist}""")
        # that is the AC pair
        hypo_vertices = pairs[np.argmax(dists)]

        # this is B : the only point not in (a,c)
        for sp in src_points:
            if not sp in hypo_vertices:
                break
        sorted_b = sp

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
        self._sorted_src_pts = sorted_src_pts
        logging.warning("Sorted detection")
        logging.warning(sorted_src_pts)

        return sorted_src_pts

    def _find_blobs(self, im, scoring_fun=None):

        if scoring_fun is None:
            scoring_fun = self._score_targets

        #grey= cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        grey=im
        rad = int(self._adaptive_med_rad * im.shape[1])
        if rad % 2 == 0:
            rad += 1

        med = np.median(grey)
        scale = 255/(med)
        cv2.multiply(grey,scale,dst=grey)
        bin = np.copy(grey)
        score_map = np.zeros_like(bin)
        for t in range(0, 255,5):
            cv2.threshold(grey, t, 255,cv2.THRESH_BINARY_INV,bin)
            if np.count_nonzero(bin) > 0.7 * im.shape[0] * im.shape[1]:
                continue
            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin,cv2.RETR_EXTERNAL,CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin,cv2.RETR_EXTERNAL,CHAIN_APPROX_SIMPLE)

            bin.fill(0)
            for c in contours:
                score = scoring_fun(c, im)
                if score >0:
                    cv2.drawContours(bin,[c],0,score,-1)
            cv2.add(bin, score_map,score_map)
        return score_map

    def _find_blobs_new(self, img, scoring_fun=None):

        grey = img
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
        bin = np.copy(grey)
        score_map = np.zeros_like(bin)
        grey_orig = grey.copy()

        for threshold in range(0, 255, 5):
            cv2.threshold(grey, threshold, 255, cv2.THRESH_BINARY_INV, bin)
            non_zero_pixels = np.count_nonzero(bin)
            # if this threshold operation leaves
            # more than 70% white pixels, continue
            # until loop is over
            if non_zero_pixels > 0.7 * grey.shape[0] * grey.shape[1]:
                continue

            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

            foreground_model = cv2.drawContours(grey.copy(), contours, -1, 255, -1)
            _, foreground_model = cv2.threshold(foreground_model, 254, 255, cv2.THRESH_BINARY)
            foreground_model = cv2.morphologyEx(foreground_model, cv2.MORPH_CLOSE, kernel = np.ones((3,3)), iterations=1)
            # cv2.imshow("foreground_model", foreground_model)
            # cv2.waitKey(0)

            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(foreground_model, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


            bin.fill(0)

            for c in contours:
                score = scoring_fun(c)
                if score > 0:
                    cv2.drawContours(bin, [c], 0, score, -1)

            score_map = cv2.add(bin, score_map)

            # if self._debug or debug:
            #     cv2.imshow("bin_th", cv2.threshold(score_map, 1, 255, cv2.THRESH_BINARY)[1])
            #     cv2.imshow("closing", foreground_model)
            #     cv2.imshow("foreground_model", foreground_model)

            #     cv2.waitKey(0)

        return score_map

    def _make_grid(self, n_col, n_row,
              top_margin=0.0, bottom_margin=0.0,
              left_margin=0.0, right_margin=0.0,
              horizontal_fill=1.0, vertical_fill=1.0,
              inside_pad=0.0, outside_pad=0.0):

        y_positions = (np.arange(n_row) * 2.0 + 1) * (1-top_margin-bottom_margin)/(2*n_row) + top_margin
        x_positions = (np.arange(n_col) * 2.0 + 1) * (1-left_margin-right_margin)/(2*n_col) + left_margin
        all_centres = [np.array([x,y]) for x,y in itertools.product(x_positions, y_positions)]

        padded_centres = []
        for center in all_centres:
            left, top = find_quadrant((1,1), center)
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


    def _points_distance(self, pt1, pt2):
        x1 , y1  = pt1
        x2 , y2  = pt2
        return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def _score_targets(self,contour, im):

        area = cv2.contourArea(contour)
        perim = cv2.arcLength(contour,True)

        if perim == 0:
            return 0
        circul =  4 * np.pi * area / perim ** 2

        if circul < .8: # fixme magic number
            return 0
        return 1

    def _score_circles(self, contour):

        area = cv2.contourArea(contour)

        if area < 400 or area > 800:
            return 0

        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        # if area was zero the functionw would have already returned
        ratio = np.pi*radius**2 / area
        # print(ratio)

        if ratio > 1 and ratio < 1.5:
            return 1
        else:
            return 0


    def _find_target_coordinates(self, img, blob_function):
        map = blob_function(img)

        _, map_bin = cv2.threshold(map, 1, 255, cv2.THRESH_BINARY)

        bin = np.zeros_like(map)

        # as soon as we have three objects, we stop
        contours = []
        for t in range(0, 255,1):
            cv2.threshold(map, t, 255,cv2.THRESH_BINARY, bin)
            if CV_VERSION == 3:
                _, contours, h = cv2.findContours(bin,cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
            else:
                contours, h = cv2.findContours(bin, cv2.RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)


            if len(contours) <3:
                raise EthoscopeException("There should be three targets. Only %i objects have been found" % (len(contours)), img)
            if len(contours) == 3:
                break

        target_diams = [cv2.boundingRect(c)[2] for c in contours]

        mean_diam = np.mean(target_diams)
        mean_sd = np.std(target_diams)

        if mean_sd/mean_diam > 0.10:
            raise EthoscopeException("Too much variation in the diameter of the targets. Something must be wrong since all target should have the same size", img)

        src_points = []
        for c in contours:
            moms = cv2.moments(c)
            x , y = moms["m10"]/moms["m00"],  moms["m01"]/moms["m00"]
            src_points.append((x,y))

        # map_bin_dots1 = place_dots(map_bin.copy(), src_points, color = 0)
        sorted_src_pts = self._sort_src_pts(src_points)
        map_bin_dots = place_dots(map_bin.copy(), sorted_src_pts, color = 0)
        # cv2.imwrite(os.path.join(os.environ["HOME"], "target_detection_segmented_dots2.png" ), map_bin_dots)
        return sorted_src_pts

    def _rois_from_img(self, img):

        self._img = img
        if os.path.exists(self._rois_pickle_file):
            with open(self._rois_pickle_file, "rb") as fh:
                import pickle
                rois = pickle.load(fh)
            return rois

        else:
            if os.path.exists(self._target_coord_file):
                with open(self._target_coord_file, "r") as fh:
                    data = fh.read()

                # each dot is in a newline
                data = data.split("\n")[:3]
                # each dot is made by two numbers separated by comma
                src_points = [tuple([int(f) for f in e.split(",")]) for e in data]
                sorted_src_pts = self._sort_src_pts(src_points)

            else:
                try:
                    sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs)
                except EthoscopeException as e:
                    # raise e
                    logging.warning("Fall back to find_blobs_new")
                    sorted_src_pts = self._find_target_coordinates(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self._find_blobs_new)
                # sorted_src_pts = self._find_target_coordinates(img)
                except Exception as e:
                    raise e

            dst_points = np.array([(0, -1),
                                   (0, 0),
                                   (-1, 0)], dtype=np.float32)
            wrap_mat = cv2.getAffineTransform(dst_points, sorted_src_pts)

            rectangles = self._make_grid(self._n_cols, self._n_rows,
                                         self._top_margin, self._bottom_margin,
                                         self._left_margin,self._right_margin,
                                         self._horizontal_fill, self._vertical_fill,
                                         self._inside_pad, self._outside_pad)

            shift = np.dot(wrap_mat, [1,1,0]) - sorted_src_pts[1] # point 1 is the ref, at 0,0
            rois = []
            side = "left"
            point = self._sorted_src_pts[2]

            for i, r in enumerate(rectangles):
                if i > 9:
                    side = "right"
                    point = self._sorted_src_pts[1]

                r = np.append(r, np.zeros((4,1)), axis=1)
                mapped_rectangle = np.dot(wrap_mat, r.T).T
                mapped_rectangle -= shift
                ct = mapped_rectangle.astype(np.int32)
                # logging.warning(i)
                ct, _, _, _ = refine_contour(ct, img, rotate=False)
                ct = pull_contour_h(ct, point, side)
                cv2.drawContours(img, [ct.reshape((1, 4, 2))], -1, (255, 0, 0), 1, LINE_AA)
                rois.append(ROI(ct, idx=i+1))

        return rois

    @staticmethod
    def _adjust(centres, n_col, n_row, pad, offset, direction=1, axis=0):

        if len(centres) != (n_col * n_row):
            raise ValueError("Number of centres should be equal to n_col * n_row")


        # sort the centers based on the value in the axis position
        # i.e. if axis is 0, sort by the 0th value, which corresponds to the x dimension
        # this results on a list with all centers in the first column, then the second, and so on
        # i.e. if axis is 1, sort by the 1st value, which corresponds to the y dimension
        # this results on a list with all centers in the first row, then the second, and so on
        all_centres_sorted = sorted(centres, key=lambda x: x[axis])
        index = -1
        sign = -1
        shape = [n_row, n_col]

        for i, centre in enumerate(all_centres_sorted):

            if i % shape[axis] == 0:
                index += 1

            if index == shape[1-axis] // 2 and shape[1-axis] % 2 != 0:
                continue

            if index >= shape[1-axis] // 2:
                sign = 1

            offset_multiplier = -index + shape[1-axis] if direction == -1 else index

            shift = np.array([sign * pad + direction* offset_multiplier * offset,] * 2)
            #shift = np.array([sign * pad + index * offset,] * 2)

            shift[1-axis] = 0

            all_centres_sorted[i] = all_centres_sorted[i] + shift

        return all_centres_sorted




class IDOCROIBuilder(TargetGridROIBuilder):
    # TODO
    pass
