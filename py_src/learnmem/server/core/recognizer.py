r"""
Track flies, record their position and draw the incoming frames
"""
import logging
import time
import traceback

from learnmem.server.core.tracking_unit import TrackingUnit
from learnmem.server.core.variables import FrameCountVariable
from learnmem.server.core.base import Base, Root
from learnmem.server.roi_builders.roi_builders import DefaultROIBuilder
from learnmem.server.utils.debug import IDOCException, EthoscopeException

__author__ = 'quentin'

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Recognizer(Base, Root):

    valid_actions = ["start", "stop", "start_saving", "prepare", "reset"]

    def __init__(
            self, tracker_class, camera_class,
            roi_builder, result_writer, drawer, *args,
            rois=None, stimulators=None, start_saving=True, video_path=None, **kwargs
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
        :param start_saving: Whether the recognizer should start saving the position of the objects immediately after start, or wait until start_saving is called.
        :type start_saving: bool
        :param args: additional arguments passed to the abstract classes
        :param kwargs: additional keyword arguments passed to the abstract classes
        """

        self._args = args
        self._kwargs = kwargs
        super().__init__(*args, **kwargs)
        self._last_frame_idx = 0
        self._force_stop = False
        self._last_positions = {}
        self._last_time_stamp = 0
        self._last_tick = 0
        self._period = 5
        self._start_saving = start_saving
        self._start_offset = 0
        self._unit_trackers = []
        self._rois = rois
        self._video_path = video_path


        self._frame_buffer = None
        self._last_t = 0

        self._submodules["drawer"] = drawer
        self._submodules["result_writer"] = result_writer
        self._submodules["camera"] = None

        try:
            self._verbose = kwargs.pop("verbose")
        except KeyError:
            self._verbose = False

        self._tracker_class = tracker_class
        self._camera_class = camera_class
        self._roi_builder = roi_builder
        self._stimulators = stimulators

    @property
    def info(self):
        self._info = {
            "status": self.status,
            "last_drawn_path": self.drawer.last_drawn_path,
            "last_annot_path": self.drawer.last_annot_path,
        }
        return self._info

    def load_camera(self):
        r"""
        Instantiate a camera object
        which can be used to sample frames
        and recognize flies
        """
        camera_args = self._config.content['io']['camera']['args']
        camera_kwargs = self._config.content['io']['camera']['kwargs']

        if self._submodules["camera"] is not None:
            logger.warning("Closing previous instance of camera")
            self._submodules["camera"].close()


        self._submodules["camera"] = self._camera_class(
            *camera_args,
            video_path=self._video_path,
            **camera_kwargs
        )


    def _build(self):
        r"""
        Build the ROIs used in the experiment
        If it fails, emit a warning and use the whole frame as the ROI
        """
        try:
            rois = self._roi_builder.build(self._submodules["camera"])

        except (IDOCException, EthoscopeException) as error: # TODO remove ethoscopexception dependency
            logger.warning(traceback.print_exc())
            logger.warning(error)
            roi_builder_class = DefaultROIBuilder
            roi_builder = roi_builder_class()
            rois = roi_builder.build(self._submodules["camera"])
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
        rois = self._build()
        self._load(*args, rois=rois, **kwargs)
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
        time_from_start = self._last_time_stamp / 1e3
        return time_from_start

    @property
    def last_frame_idx(self):
        """
        :return: The number of the last acquired frame.
        :rtype: int
        """
        return self._last_frame_idx

    def start_saving(self, start_offset=None):
        """
        Call this method to sync the time of the recognizer with the time
        of other processes running in IDOC i.e. the controller
        When called, it signals the recognizer that it can start saving i.e.
        record the position of the flies to the result_writer
        If given no start_offset, it is computed as the difference between
        now and when the run() method started executing. If given a start offet,
        it is set as the start offset of the recognizer.
        """
        self._start_saving = True

        if start_offset is None:
            self._start_offset = time.time() - self._time_zero
        else:
            self._start_offset = start_offset

    @property
    def start_offset_ms(self):
        """
        Return the offset time that must be substracted
        to align the recognizer with other processes
        e.g. controller from the camera time in ms
        """
        return self._start_offset * 1000

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
            logger.info("Monitor starting a run")

            for items in enumerate(self.camera):

                i, (t_ms, frame) = items

                if self.stopped:
                    logger.info("Monitor object stopped from external request")
                    break

                self._last_frame_idx = i
                self._last_time_stamp = t_ms
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

                    if self.result_writer is not None and self._start_saving:
                        frame_count = FrameCountVariable(i)
                        data_rows[0].append(frame_count)
                        self.result_writer.write(
                            # time in ms since start_saving
                            t_ms - self.start_offset_ms,
                            # pass roi to tell the result writer the fly id
                            track_u.roi,
                            # actual tracking data
                            data_rows
                        )

                if self.drawer is not None:
                    annot = self.drawer.draw(frame, tracking_units=self._unit_trackers, positions=self._last_positions)
                    tick = int(round((t_ms/1000.0)/self._period))

                    if tick > self._last_tick:
                        self.drawer.write(frame, annot)

                    self._last_tick = tick

                self._last_t = t_ms


        except Exception as error:
            logger.warning("Monitor closing with an exception")
            logger.warning(traceback.format_exc())
            raise error

        finally:
            logger.info("Monitor closing")
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
        #     rois=self._rois, stimulators=self._stimulators, start_saving=True, video_path=self._video_path, **self._kwargs
        # )
