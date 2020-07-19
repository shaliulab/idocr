__author__ = 'quentin'

import logging
import os

import cv2

from idoc.server.core.base import Base, Root
from idoc.configuration import IDOCConfiguration


try:
    from cv2.cv import CV_FOURCC as VideoWriter_fourcc
    from cv2.cv import CV_AA as LINE_AA
except ImportError:
    from cv2 import VideoWriter_fourcc
    from cv2 import LINE_AA

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BaseDrawer(Base, Root):

    _font = cv2.FONT_HERSHEY_COMPLEX_SMALL
    _black_colour = (0, 0, 0)
    _roi_colour = (0, 255, 0)
    _quality = cv2.IMWRITE_JPEG_QUALITY
    _interaction_colour = (255, 0, 0)
    _standard_colour = (0, 0, 255)

    def __init__(self, *args, video_out=None, draw_frames=True, video_out_fourcc="DIVX", framerate=2, **kwargs):
        """
        A template class to annotate and save the processed frames. It can also save the annotated frames in a video
        file and/or display them in a new window. The :meth:`~ethoscope.drawers.drawers.BaseDrawer._annotate_frame`
        abstract method defines how frames are annotated.

        :param video_out: The path to the output file (.avi)
        :type video_out: str
        :param draw_frames: Whether frames should be displayed on the screen (a new window will be created).
        :type draw_frames: bool
        :param video_out_fourcc: When setting ``video_out``, this defines the codec used to save the output video (see `fourcc <http://www.fourcc.org/codecs.php>`_)
        :type video_out_fourcc: str
        :param framerate: When setting ``video_out``, this defines the output fps. typically, the same as the input fps.
        :type framerate: float
        """
        super().__init__(*args, **kwargs)
        self._settings.update({"framerate": None})

        self.video_out = video_out
        self._draw_frames = draw_frames
        self._video_writers = {}
        self._window_name = "ethoscope_" + str(os.getpid())
        self._video_out_fourcc = video_out_fourcc
        self._settings['framerate'] = framerate
        if draw_frames:
            cv2.namedWindow(self._window_name, cv2.WINDOW_AUTOSIZE)
        self._last_drawn_frame = None
        self.arena = None
        self._frame_count = 0
        self._original_video = None
        self._annotated_video = None


    @property
    def frame_count(self):
        return self._frame_count


    def framerate(self):
        return round(self._settings['framerate'])


    def _annotate_frame(self, img, tracking_units, positions, roi, metadata=None):
        """
        Abstract method defining how frames should be annotated.
        The `img` array, which is passed by reference, is meant to be modified by this method.

        :param img: the frame that was just processed
        :type img: :class:`~numpy.ndarray`
        :param positions: a list of positions resulting from analysis of the frame
        :type positions: list(:class:`~ethoscope.core.data_point.DataPoint`)
        :param tracking_units: the tracking units corresponding to the positions
        :type tracking_units: list(:class:`~ethoscope.core.tracking_unit.TrackingUnit`)
        :return:
        """
        raise NotImplementedError

    @property
    def last_drawn_frame(self):
        return self._last_drawn_frame

    @property
    def last_drawn_path(self):
        return self._config.content["drawer"]["last_drawn_path"]

    @property
    def last_annot_path(self):
        return self._config.content["drawer"]["last_annot_path"]

    def write_frames(self):

        cv2.imwrite(self.last_drawn_path, self._last_raw_frame, [int(self._quality), 50])
        cv2.imwrite(self.last_annot_path, self._last_annot_frame, [int(self._quality), 50])

    def write_videos(self, video_root='video.avi'):


        if len(self._video_writers) == 0:

            # TODO More elegant way of deriving the path
            self._original_video = video_root.replace(".avi", "_ORIGINAL.avi")
            self._annotated_video = video_root.replace(".avi", "_ANNOTATED.avi")

            logger.info('Videos will be saved to:')
            logger.info(self._original_video)
            logger.info(self._annotated_video)
            logger.info('With video framerate %s', self.framerate)

            self._video_writers = {

                "ORIGINAL": cv2.VideoWriter(
                    # path to resulting video
                    self._original_video,
                    # codec
                    VideoWriter_fourcc(*self._video_out_fourcc),
                    # framerate
                    self.framerate,
                    # resolution (reverse of first two dims in shape)
                    (self._last_raw_frame.shape[1], self._last_raw_frame.shape[0])
                ),

                "ANNOTATED": cv2.VideoWriter(
                    # path to resulting video
                    self._annotated_video,
                    # codec
                    VideoWriter_fourcc(*self._video_out_fourcc),
                    # framerate
                    self.framerate,
                    # resolution (reverse of first two dims in shape)
                    (self._last_annot_frame.shape[1], self._last_annot_frame.shape[0])
                )
            }

        if len(self._video_writers) == 2:
            self._video_writers["ORIGINAL"].write(self._last_raw_frame)
            self._video_writers["ANNOTATED"].write(self._last_annot_frame)


    def draw(self, img, tracking_units, positions, roi=True, metadata=None):
        """
        Draw results on a frame.

        :param img: the frame that was just processed
        :type img: :class:`~numpy.ndarray`
        :param positions: a list of positions resulting from analysis of the frame by a tracker
        :type positions: list(:class:`~ethoscope.core.data_point.DataPoint`)
        :param tracking_units: the tracking units corresponding to the positions
        :type tracking_units: list(:class:`~ethoscope.core.tracking_unit.TrackingUnit`)
        :return:
        """

        self._last_drawn_frame = img.copy()
        self._last_raw_frame = img.copy()

        img = self._annotate_frame(self._last_drawn_frame, tracking_units, positions, roi, metadata=metadata)
        self._last_annot_frame = img

        if self._draw_frames:
            cv2.imshow(self._window_name, self._last_drawn_frame)
            cv2.waitKey(0)

        if self.video_out is None:
            return self._last_drawn_frame

        self._frame_count += 1
        return self._last_drawn_frame

    def __del__(self):

        if super().stop():
            return

        if self._draw_frames:
            cv2.waitKey(1)
            cv2.destroyAllWindows()
            cv2.waitKey(1)

        for video_writer in self._video_writers.values():
            logger.info('Releasing video writer')
            video_writer.release()

    def close(self):
        # logger.warning("Drawer has drawn %d frames", self._frame_count)
        self.__del__()


class NullDrawer(BaseDrawer):
    def __init__(self):
        """
        A drawer that does nothing (no video writing, no annotation, no display on the screen).

        :return:
        """
        super(NullDrawer, self).__init__(draw_frames=False)

    def _annotate_frame(self, img, tracking_units, positions, roi, metadata=None):
        pass


class DefaultDrawer(BaseDrawer):
    def __init__(self, *args, **kwargs):
        """
        The default drawer. It draws ellipses on the detected objects and polygons around ROIs. When an "interaction"
        see :class:`~ethoscope.stimulators.stimulators.BaseInteractor` happens within a ROI,
        the ellipse is red, blue otherwise.

        :param video_out: The path to the output file (.avi)
        :type video_out: str
        :param draw_frames: Whether frames should be displayed on the screen (a new window will be created).
        :type draw_frames: bool
        """
        super().__init__(*args, **kwargs)

    def _annotate_frame(self, img, tracking_units, positions=None, roi=True, metadata=None):
        if img is None:
            return

        for track_u in tracking_units:

            x, y = track_u.roi.offset
            y += track_u.roi.rectangle[3]/2


            if roi:
                text_pos = (int(x), int(y))
                cv2.putText(img, str(track_u.roi.idx), text_pos, self._font, 1, (255, 255, 0))
                cv2.drawContours(img, [track_u.roi.polygon], -1, self._black_colour, 3, LINE_AA)
                cv2.drawContours(img, [track_u.roi.polygon], -1, self._roi_colour, 1, LINE_AA)

            if positions is not None:
                try:
                    pos_list = positions[track_u.roi.idx]
                except KeyError:
                    continue

                colour = self._standard_colour

                for pos in pos_list:
                    try:
                        if pos["has_interacted"]:
                            colour = self._interaction_colour
                    except KeyError:
                        pass

                    cv2.ellipse(img, ((pos["x"], pos["y"]), (pos["w"], pos["h"]), pos["phi"]), self._black_colour, 3, LINE_AA)
                    cv2.ellipse(img, ((pos["x"], pos["y"]), (pos["w"], pos["h"]), pos["phi"]), colour, 1, LINE_AA)

            if metadata is not None:
                cv2.putText(img, metadata["time"], (50, 30), self._font, 2, (255, 255, 255))
                cv2.putText(img, "%s" % str(metadata["frame"]).zfill(5), (img.shape[1] - 250, 30), self._font, 2, (255, 255, 255))
                cv2.putText(img, "%s" % str(metadata["framerate"]).zfill(2), (img.shape[1] - 100, 30), self._font, 2, (255, 255, 255))


        return img

# TODO Finish this when you have time
# class AnnotationDrawer(BaseDrawer):
#     def __init__(self, video_out= None, draw_frames=False):
#         """
#         The annotation drawer. It draws dots and arrows on the detected objects and polygons around ROIs,
#         instead of an ellipse, so the user can see the contours of the fly while knowing where the tracker
#         thinks the fly is

#         :param video_out: The path to the output file (.avi)
#         :type video_out: str
#         :param draw_frames: Whether frames should be displayed on the screen (a new window will be created).
#         :type draw_frames: bool
#         """
#         super(AnnotationDrawer, self).__init__(video_out=video_out, draw_frames=draw_frames)

#     def _annotate_frame(self,img, tracking_units, positions=None, roi=True):
#         if img is None:
#             return

#         roi_colour = (0, 255,0)
#         for track_u in tracking_units:

#             x,y = track_u.roi.offset
#             y += track_u.roi.rectangle[3]/2
#             black_colour = (0, 0,0)

#             if roi:
#                 cv2.putText(img, str(track_u.roi.idx), (int(x)*5,int(y)), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255,255,0))
#                 cv2.drawContours(img,[track_u.roi.polygon],-1, black_colour, 3, LINE_AA)
#                 cv2.drawContours(img,[track_u.roi.polygon],-1, roi_colour, 1, LINE_AA)

#             if positions is not None:
#                 try:
#                     pos_list = positions[track_u.roi.idx]
#                 except KeyError:
#                     continue

#                 for pos in pos_list:
#                     colour = (0 ,0, 255)
#                     try:
#                         if pos["has_interacted"]:
#                             colour = (255, 0,0)
#                     except KeyError:
#                         pass

#                     # cv2.ellipse(img,((pos["x"],pos["y"]), (pos["w"],pos["h"]), pos["phi"]),black_colour,3, LINE_AA)
#                     # cv2.ellipse(img,((pos["x"],pos["y"]), (pos["w"],pos["h"]), pos["phi"]),colour,1, LINE_AA)
#                     cv2.circle(img, (pos["x"], pos["y"]), 3, black_colour, -1)
#                     cv2.arrowedLine(img, (pos))

#                     distance_raw = round(10**(pos["distance"]/1000), 5)
#                     x,y = self.roi.offset
#                     # x += 0.9*self.roi.rectangle[3]
#                     y += self.roi.rectangle[3]/2

#                     cv2.putText(out, str(distance_raw), (int(x), int(y)), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 255, 0))


#         return img
