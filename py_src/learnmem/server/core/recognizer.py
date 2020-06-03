r"""
Track flies, record their position and draw the incoming frames
"""
import logging
import traceback


from learnmem.server.core.tracking_unit import TrackingUnit
from learnmem.server.core.variables import FrameCountVariable
from learnmem.server.core.base import Base, Root

__author__ = 'quentin'

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Recognizer(Base, Root):

    def __init__(self, camera, tracker_class,
                result_writer, drawer, *args,
                 rois=None, stimulators=None,
                 **kwargs
                 # extra arguments for the tracker objects
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
        :type stimulators: list(:class:`~ethoscope.stimulators.stimulators.BaseInteractor`
        :param args: additional arguments passed to the tracking algorithm
        :param kwargs: additional keyword arguments passed to the tracking algorithm
        """
        super().__init__()

        self._submodules["camera"] = camera
        self._last_frame_idx = 0
        self._force_stop = False
        self._last_positions = {}
        self._last_time_stamp = 0
        self._last_tick = 0
        self._period = 5


        self._frame_buffer = None
        self._last_t = 0

        self._submodules["drawer"] = drawer
        self._submodules["result_writer"] = result_writer

        try:
            self._verbose = kwargs.pop("verbose")
        except KeyError:
            self._verbose = False

        if rois is None:
            raise NotImplementedError("rois must exist (cannot be None)")

        if stimulators is None:
            
            self._unit_trackers = [TrackingUnit(tracker_class, r, None, *args, **kwargs) for r in rois]

        elif len(stimulators) == len(rois):
            self._unit_trackers = [TrackingUnit(tracker_class, r, inter, *args, **kwargs) for r, inter in zip(rois, stimulators)]
        else:
            raise ValueError("You should have one interactor per ROI")



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
        :return: The time, in seconds, since monitoring started running. It will be 0 if the monitor is not running yet.
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

    def stop(self):
        """
        Interrupts the `run` method. This is meant to be called by another thread to stop monitoring externally.
        """
        self._force_stop = True

    def run(self):
        # , result_writer=None, drawer=None

        """
        Runs the monitor indefinitely.

        :param result_writer: A result writer used to control how data are saved. `None` means no results will be saved.
        :type result_writer: :class:`~ethoscope.utils.io.ResultWriter`
        :param drawer: A drawer to plot the data on frames, display frames and/or save videos. `None` means none of the aforementioned actions will performed.
        :type drawer: :class:`~ethoscope.drawers.drawers.BaseDrawer`
        """


        super().run()
        try:
            logger.info("Monitor starting a run")

            for x in enumerate(self.camera):

                i, (t_ms, frame) = x

                if self._force_stop:
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

                    if self.result_writer is not None:
                        frame_count = FrameCountVariable(i)
                        data_rows[0].append(frame_count)
                        self.result_writer.write(t_ms, track_u.roi, data_rows)


                if self.drawer is not None:
                    annot = self.drawer.draw(frame, tracking_units=self._unit_trackers, positions=self._last_positions)

                    tick = int(round((t_ms/1000.0)/self._period))


                    if tick == self._last_tick:
                        pass
                    else:
                        self.drawer.write(frame, annot)

                    self._last_tick = tick

                self._last_t = t_ms


        except Exception as e:
            logger.warning("Monitor closing with an exception")
            logger.warning(traceback.format_exc())
            raise e

        finally:
            logger.info("Monitor closing")
            self.stop()

    @property
    def info(self):
        self._info = {
            "status": self.status,
            "last_drawn_path": self.drawer.last_drawn_path,
            "last_annot_path": self.drawer.last_annot_path,
        }
        return self._info