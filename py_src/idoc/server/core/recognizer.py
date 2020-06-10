"""
Track flies, record their position and draw the incoming frames
"""
import datetime
import logging
import time
import traceback

from idoc.server.core.tracking_unit import TrackingUnit
from idoc.server.core.variables import FrameCountVariable
from idoc.server.core.base import Base, Root
from idoc.server.roi_builders.roi_builders import DefaultROIBuilder
from idoc.server.utils.debug import IDOCException, EthoscopeException
from idoc.helpers import iso_format, hours_minutes_seconds

__author__ = 'quentin'

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Recognizer(Base, Root):

    valid_actions = ["start", "stop", "prepare", "reset"]

    def __init__(
            self, tracker_class, camera_class,
            roi_builder, result_writer, drawer,
            rois=None, stimulators=None,
            user_data=None,
            adaptation_offset=0
        ):
        """
        Class to orchestrate the tracking of multiple objects.
        It performs, in order, the following actions:

         * Requesting raw frames (delegated to :class:`~ethoscope.hardware.input.cameras.BaseCamera`)
         * Cutting frame portions according to the ROI layout (delegated to :class:`~ethoscope.core.tracking_unit.TrackingUnit`).
         * Detecting animals and computing their positions and other variables (delegated to :class:`~ethoscope.trackers.trackers.BaseTracker`).
         * Using computed variables to interact physically (i.e. feed-back) with the animals (delegated to :class:`~ethoscope.stimulators.stimulators.BaseStimulator`).
         * Drawing results on a frame, optionally saving video (delegated to :class:`~ethoscope.drawers.drawers.BaseDrawer`).
         * Saving the result of tracking in a database (delegated to :class:`~ethoscope.utils.io.ResultWriter`).

        :param camera: a camera object responsible of acquiring frames and associated time stamps
        :type camera: :class:`~ethoscope.hardware.input.cameras.BaseCamera`
        :param tracker_class: The algorithm that will be used for tracking. It must inherit from :class:`~ethoscope.trackers.trackers.BaseTracker`
        :type tracker_class: class
        :param rois: A list of region of interest.
        :type rois: list(:class:`~ethoscope.core.roi.ROI`)
        :param stimulators: The class that will be used to analyse the position of the object and interact with the system/hardware.
        :type stimulators: list(:class:`~ethoscope.stimulators.stimulators.BaseInteractor`)
        :type stimulators: list(:class:`~ethoscope.stimulators.stimulators.BaseInteractor`)
        :param args: additional arguments passed to the abstract classes
        :param kwargs: additional keyword arguments passed to the abstract classes
        """

        super().__init__()
        self._user_data = user_data

        # print("user_data")
        # print(user_data)
        self._last_frame_idx = 0
        self._force_stop = False
        self._last_positions = {}
        self._last_time_stamp = 0
        self._last_tick = 0
        self._period = 5
        self._adaptation_offset = adaptation_offset
        self._unit_trackers = []
        self._rois = rois
        self._frame_buffer = None
        self.rois = []

        self._add_submodule("drawer", drawer)
        self._add_submodule("result_writer", result_writer)
        self._submodules["camera"] = None

        self._tracker_class = tracker_class
        self._camera_class = camera_class
        self._roi_builder = roi_builder
        self._stimulators = stimulators

        self._last_frames = []
        self._last_times = []



    @property
    def last_t(self):
        return self.last_time_stamp

    @property
    def info(self):
        self._info = {
            "status": self.status,
            "last_drawn_path": self.drawer.last_drawn_path,
            "last_annot_path": self.drawer.last_annot_path,
            "camera": self.camera.__class__.__name__
        }
        return self._info

    def load_camera(self):
        r"""
        Instantiate a camera object
        which can be used to sample frames
        and recognize flies.
        This way the camera is actually not initialized
        until this method is called in the recognizer.prepare method
        i.e. not at Recognizer.__init__.
        """
        camera_args = self._config.content['io']['camera']['args']
        camera_kwargs = self._config.content['io']['camera']['kwargs']

        if self._submodules["camera"] is not None:
            logger.warning("Closing previous instance of camera")
            self._submodules["camera"].close()


        user_data = self._user_data.copy()
        # Pass settings the user may have passed upon starting the program
        # kwargs to be passed on initialization of camera class
        camera_kwargs["video_path"] = user_data.pop("video_path")
        camera_kwargs["max_duration"] = user_data.pop("max_duration") or self._config.content['experiment']['max_duration']
        if user_data["use_wall_clock"] is not None:
            camera_kwargs["use_wall_clock"] = user_data.pop("use_wall_clock")
        else:
            camera_kwargs["use_wall_clock"] = self._config.content['io']['camera']['kwargs']['use_wall_clock']


        self._submodules["camera"] = self._camera_class(
            *camera_args,
            **camera_kwargs
        )

        # Pass settings the user may have passed upon starting the program
        # kwargs that can be passed afterwards

        if user_data is not None:
            for setting in user_data:
                if setting in self._submodules["camera"].settings:
                    if user_data[setting] is not None:
                        # logger.debug("Assigning ", setting, "to camera")
                        self._submodules["camera"].settings[setting] = user_data[setting]
                    else:
                        pass
                        # logger.debug("Not assigning ", setting, "to camera. Input value is None")

                else:
                    pass
                    # logger.debug("Not assigning ", setting, "to camera. Setting does not belong")

        self._settings['camera'] = self.camera.settings

    def _build(self):
        r"""
        Build the ROIs used in the experiment
        If it fails, emit a warning and use the whole frame as the ROI
        """
        try:
            rois = self._roi_builder.build(self.camera)

        except (IDOCException, EthoscopeException) as error: # TODO remove ethoscopexception dependency
            logger.warning(traceback.print_exc())
            logger.warning(error)
            roi_builder_class = DefaultROIBuilder
            roi_builder = roi_builder_class()
            rois = roi_builder.build(self.camera)
            logger.debug("Default ROI loaded")

        return rois


    def _load(self, *args, rois=None, **kwargs):
        r"""
        Populate the unit_trackers slot which is iteratively gone through
        on every loop in run, to track every ROI independently
        """

        if rois is None:
            rois = self._rois
            if rois is None:
                raise NotImplementedError("rois must exist (cannot be None)")

        if self._stimulators is None:

            self._unit_trackers = [TrackingUnit(self._tracker_class, r, None, *args, **kwargs) for r in rois]

        elif len(self._stimulators) == len(rois):
            self._unit_trackers = [TrackingUnit(self._tracker_class, r, inter, *args, **kwargs) for r, inter in zip(rois, self._stimulators)]
        else:
            raise ValueError("You should have one interactor per ROI")

    def prepare(self, *args, **kwargs):
        """
        Open the camera, build the ROIs and bind them to the trackers
        """
        self.load_camera()
        self.rois = self._build()
        self._load(*args, rois=self.rois, **kwargs)
        self.ready = True

    @property
    def camera(self):
        return self._submodules["camera"]

    @property
    def drawer(self):
        return self._submodules["drawer"]

    @property
    def result_writer(self):
        return self._submodules["result_writer"]

    @property
    def last_positions(self):
        """
        :return: The last positions (and other recorded variables) of all detected animals
        :rtype: dict
        """
        return self._last_positions

    @property
    def last_time_stamp(self):
        """
        :return: The time, in seconds, since recognizer started running. It will be 0 if the monitor is not running yet.
        :rtype: float
        """
        self._last_time_stamp
        return self._last_time_stamp

    @last_time_stamp.setter
    def last_time_stamp(self, last_time_stamp):

        last_time_stamp_s = last_time_stamp / 1e3

        # print(self._last_times)

        if len(self._last_times) == 10:
            self._last_times.pop(0)

        self._last_times.append(last_time_stamp_s)
        self._last_time_stamp = last_time_stamp_s


    @property
    def last_frame_idx(self):
        """
        :return: The number of the last acquired frame.
        :rtype: int
        """
        return self._last_frame_idx

    @last_frame_idx.setter
    def last_frame_idx(self, last_frame_idx):
        """
        :return: The number of the last acquired frame.
        :rtype: int
        """
        if len(self._last_frames) == 10:
            self._last_frames.pop(0)

        self._last_frames.append(last_frame_idx)
        self._last_frame_idx = last_frame_idx


    @property
    def fps(self):

        try:
            # print(self._last_frames)
            # print(self._last_times)
            end_f, start_f = (self._last_frames[::-1][0], self._last_frames[0])
            end_t, start_t = (self._last_times[::-1][0], self._last_times[0])
            # print(end_f, start_f, end_t, start_t)
        except IndexError:
            return 0

        try:
            framerate = (end_f - start_f) / (end_t - start_t)
        except ZeroDivisionError:
            framerate = 0

        return framerate

    def run(self):
        """
        Runs the monitor indefinitely.

        :param result_writer: A result writer used to control how data are saved. `None` means no results will be saved.
        :type result_writer: :class:`~ethoscope.utils.io.ResultWriter`
        :param drawer: A drawer to plot the data on frames, display frames and/or save videos. `None` means none of the aforementioned actions will performed.
        :type drawer: :class:`~ethoscope.drawers.drawers.BaseDrawer`
        """

        if self.ready is not True:
            return

        super().run()

        try:
            logger.info("Recognizer starting a run")

            for items in enumerate(self.camera):

                i, (t_ms, frame) = items

                # if self._user_data["sync"]:
                #     while t_ms > (self.elapsed_seconds * 1000):
                #         time.sleep(0.1)

                if self.result_writer is not None:
                    self.result_writer.last_t = self.last_t

                # logger.warning('Reading  frame at %d', t_ms)

                if self.stopped:
                    logger.info("Recognizer object stopped from external request")
                    break

                self.last_frame_idx = i
                self.last_time_stamp = t_ms
                self._frame_buffer = frame

                # if quality_controller is not None:
                #     qc = quality_controller.qc(frame)
                #     quality_controller.write(t, qc)

                for _, track_u in enumerate(self._unit_trackers):
                    data_rows = track_u.track(t_ms, frame)
                    if len(data_rows) == 0:
                        self._last_positions[track_u.roi.idx] = []
                        continue

                    abs_pos = track_u.get_last_positions(absolute=True)

                    # if abs_pos is not None:
                    self._last_positions[track_u.roi.idx] = abs_pos

                    if self.result_writer is not None:
                        frame_count = FrameCountVariable(i)
                        data_rows[0].append(frame_count)
                        self.result_writer.write(
                            # pass roi to tell the result writer the fly id
                            track_u.roi,
                            # actual tracking data
                            data_rows
                        )

                metadata = {
                    "time": iso_format(hours_minutes_seconds(self.last_t)),
                    "frame": self._last_frame_idx,
                    "framerate": round(self.fps)
                }

                if self.drawer is not None:
                    # logger.debug("Drawing frame %d", i)
                    # annot = self.drawer.draw(frame, tracking_units=self._unit_trackers, positions=self._last_positions)
                    annot = self.drawer.draw(frame, tracking_units=self._unit_trackers, positions=self._last_positions, metadata=metadata)
                    tick = int(round((t_ms/1000.0)/self._period))

                    if tick > self._last_tick:
                        # logger.debug("Writing frame %d", i)
                        self.drawer.write(frame, annot)

                    self._last_tick = tick




        except Exception as error:
            logger.warning("Recognizer closing with an exception")
            logger.warning(traceback.format_exc())
            raise error

        finally:
            logger.info("Recognizer closing")
            self.stop()

    def stop(self):
        super().stop()

        if self.camera is not None:
            self.camera.close()
        if self.drawer is not None:
            self.drawer.close()

    def reset(self):
        super().reset()
        # TODO Even after redoing the instance by calling __init__
        # I still get
        # RuntimeError: threads can only be started once

        # self.__init__(
        #     self._tracker_class, self._camera_class,
        #     self._submodules['roi_builder'], self._submodules['result_writer'], self._submodules['drawer'], *self._args,
        #     rois=self._rois, stimulators=self._stimulators, video_path=self._video_path, **self._kwargs
        # )

if __name__ == "__main__":

    import argparse

    from idoc.server.trackers.adaptive_bg_tracker import AdaptiveBGModel
    from idoc.server.io.pylon_camera import PylonCamera
    from idoc.server.io.opencv_camera import OpenCVCamera
    from idoc.server.io.result_writer import CSVResultWriter
    from idoc.server.roi_builders.target_roi_builder import IDOCROIBuilder
    from idoc.server.drawers.drawers import DefaultDrawer

    def main():

        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--camera", type=str, choices=["PylonCamera", "OpenCVCamera"], default="OpenCVCamera")
        ARGS = vars(parser.parse_args())

        camera_class_mame = ARGS["camera"]

        for camera_class in [PylonCamera, OpenCVCamera]:
            if camera_class_mame == camera_class.__name__:
                break

        roi_builder = IDOCROIBuilder()
        result_writer = CSVResultWriter(start_datetime="2000-01-01_00-00-00")
        drawer = DefaultDrawer(draw_frames=False)

        recognizer = Recognizer(
            AdaptiveBGModel, camera_class,
            roi_builder, result_writer, drawer
        )

        recognizer.prepare()

    main()
