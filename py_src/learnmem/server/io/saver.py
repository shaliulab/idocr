# Standard library imports
import logging
import os
import os.path
from threading import Event
import traceback

# Third party imports
import cv2
import pandas as pd

# Local application imports
# from learnmem.decorators import if_record_event, if_not_record_end_event
from learnmem.configuration import LearnMemConfiguration
from learnmem.helpers import get_machine_id, get_machine_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CFG = LearnMemConfiguration()

MAX_N_ROWS_TO_INSERT = CFG.content["io"]["max_n_rows_to_insert"]

# Set up package configurations

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
class SimpleSaver:

    output_dir = ""
    store = None
    store_video = None
    out = None
    video_writers = None
    _columns = []
    _output_csv = ""
    _record_event = Event()
    _stop_event = Event()
    resolution = (None, None)
    framerate = 0
    _cache = None

    def __init__(self, control, track, result_dir, cache=None):

        if cache is not None:
            self._cache.extend(cache)
        else:
            self._cache = []

        self.control = control
        self.track = track
        self._machine_id = get_machine_id()
        self._machine_name = get_machine_name()
        self.result_dir = result_dir

    def set_columns(self, columns):
        self._columns = columns


    def stop(self):
        self._stop_event.set()
        logger.info("csv file is %s", self._output_csv)

        if self.track:
            self.stop_video()


    def launch(self, start_datetime, resolution=None, framerate=None):
        """
        Set absolute paths to output (depend on what time the record button is pressed)
        and create directory structure if needed.
        """

        # prepare output directories
        self.output_dir = os.path.join(
            self.result_dir,  # root
            self._machine_id,
            self._machine_name,
            start_datetime
        )

        logger.info('Output will be saved in %s', self.output_dir)

        logger.info("Creating output directory structures")
        os.makedirs(self.output_dir, exist_ok=False)
        # os.mkdirs(os.path.join(self.output_dir, "frames"))

        prefix = start_datetime + '_learnmem_' + self._machine_id

        self._output_csv = os.path.join(self.output_dir, prefix + ".csv")

        store_header = pd.DataFrame(columns=self._columns)
        with open(self._output_csv, 'w') as store:
            store_header.to_csv(store)


        if self.track:
            # initialize video and csv storage
            video_out_fourcc = ['H264', 'XVID', 'MJPG', 'DIVX', 'FMP4', 'MP4V']
            vifc = video_out_fourcc[3]

            video_format = CFG.content["saver"]["video_format"]
            self.framerate = CFG.content["saver"]["framerate"] or framerate
            self.resolution = CFG.content["saver"]["resolution"] or resolution

            logger.info('FPS of output videos: %.3f', framerate)

            self.video_writers = [
                cv2.VideoWriter(
                    os.path.join(self.output_dir, prefix + suffix + video_format),
                    cv2.VideoWriter_fourcc(*vifc),
                    self.framerate, self.resolution
                ) for suffix in ["_original.", "_annotated."]]

            self._record_event.set()
        else:
            self._record_event.set()

    def save_odors(self, odor_A, odor_B):
        path2file = os.path.join(self.output_dir, "odors.csv")
        handle = open(path2file, 'w')
        handle.write('odor_A,odor_B\n')
        handle.write('{},{}\n'.format(odor_A, odor_B))
        handle.close()

    def process_row(self, d):
        """
        Append row d to the store
        append the list of rows to the HDF5 store and clear the list.
        """

        if not self._record_event.is_set():
            logger.warning("record event is not yet set. Your data will not be saved")

            return

        if self._stop_event.is_set():
            self.store_and_clear()
            return

        if len(self._cache) >= MAX_N_ROWS_TO_INSERT:
            self.store_and_clear()

        probe = {
            hardware: d[hardware] for hardware in
            d if hardware in [e.ljust(16) for e in
            ["ODOR_A_LEFT", "ODOR_A_RIGHT", "ODOR_B_LEFT", "ODOR_B_RIGHT"]]
        }

        logger.debug(probe)
        self._cache.append(d)
        # logger.warning(self._cache)

    def store_and_clear(self):
        """
        Convert the cache list to a DataFrame and append that to HDF5.
        """

        try:
            df = pd.DataFrame.from_records(self._cache)[self._columns]

        except KeyError as e:
            logger.warning("No data was collected. Did you press the record button?")
            logger.warning(traceback.print_exc())
            logger.warning(self._cache)
            logger.warning(self._columns)
            raise e

        except Exception as e:
            logger.warning('There was an error saving the data')
            logger.warning(traceback.print_exc())
            logger.warning(self._cache)
            logger.warning(self._columns)
            raise e
        else:
            self._cache.clear()


        # check the dataframe is not empty
        # could be empty if user closes before recording anything

        logger.debug("Saving cache to %s", self._output_csv)

        # save to csv
        try:
            # append data
            with open(self._output_csv, "a") as fh:
                df.to_csv(fh, header=False)

        except FileNotFoundError:
            logger.warning('File already removed. Not saving cache')

    def save_video(self, frame_anot, frame_orig):

        if not self._record_event.is_set():
            return

        imgs = [frame_orig, frame_anot]
        imgs_3_channels = []

        for img in imgs:
            if len(img.shape) == 3:
                pass
            else:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            imgs_3_channels.append(img)

        if not self.video_writers is None:
            for img, video_writer in zip(imgs_3_channels, self.video_writers):
                saved_frame = cv2.resize(img, self.resolution)
                video_writer.write(saved_frame)

    def stop_video(self):

        for video_writer in self.video_writers:
            video_writer.release()
