# Standard library imports
import logging
import os
import os.path
import traceback

# Third party imports
import cv2
import pandas as pd

# Local application imports
# from learnmem.decorators import if_record_event, if_not_record_end_event
from learnmem.configuration import LearnMemConfiguration
from learnmem.helpers import get_machine_id, get_machine_name
from learnmem.server.core.base import Settings, Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

config = LearnMemConfiguration()

MAX_N_ROWS_TO_INSERT = config.content["io"]["max_n_rows_to_insert"]

#TODO Needs refactoring
class SimpleSaver(Settings, Root):
    r"""
    Save results to a csv file styled in the format:
        start_datetime + '_learnmem_' + self._machine_id + .csv
    """

    output_dir = ""
    store = None
    store_video = None
    out = None
    video_writers = None
    _columns = []
    _output_csv = ""
    resolution = (None, None)

    def __init__(self, result_dir, *args, control=False, track=False, **kwargs):


        self._cache = {}
        self.control = control
        if self.control:
            self._cache['control'] = []
        self.track = track
        if self.track:
            self._cache['track'] = []

        self.result_dir = result_dir
        config = LearnMemConfiguration()
        self.video_format = config.content["saver"]["video_format"]
        self.framerate = config.content["saver"]["framerate"]
        self.resolution = config.content["saver"]["resolution"]

        super().__init__(*args, **kwargs)


    def set_columns(self, columns):
        self._columns = columns


    def stop(self):
        pass

        # self.stop_video()
        # for cache in self._cache:
        #     self.store_and_clear(cache)

    def launch(self, start_datetime, resolution=None, framerate=None):
        """
        Set absolute paths to output (depend on what time the record button is pressed)
        and create directory structure if needed.
        """

        # prepare output directories
        self.output_dir = os.path.join(
            self.result_dir,  # root
            get_machine_id(),
            get_machine_name(),
            start_datetime
        )

        logger.info('Output will be saved in %s', self.output_dir)

        logger.info("Creating output directory structures")
        os.makedirs(self.output_dir, exist_ok=False)
        # os.mkdirs(os.path.join(self.output_dir, "frames"))

        prefix = start_datetime + '_learnmem_' + get_machine_id()

        self._output_csv = os.path.join(self.output_dir, prefix + ".csv")

        store_header = pd.DataFrame(columns=self._columns)
        with open(self._output_csv, 'w') as store:
            store_header.to_csv(store)


        if self.track:
            # initialize video and csv storage
            video_out_fourcc = ['H264', 'XVID', 'MJPG', 'DIVX', 'FMP4', 'MP4V']
            vifc = video_out_fourcc[3]



            logger.info('FPS of output videos: %.3f', framerate)

            self.video_writers = [
                cv2.VideoWriter(
                    os.path.join(self.output_dir, prefix + suffix + self.video_format),
                    cv2.VideoWriter_fourcc(*vifc),
                    self.framerate, self.resolution
                ) for suffix in ["_original.", "_annotated."]]


    def save_odors(self, odor_a, odor_b):
        path2file = os.path.join(self.output_dir, "odors.csv")
        handle = open(path2file, 'w')
        handle.write('odor_a,odor_b\n')
        handle.write('{},{}\n'.format(odor_a, odor_b))
        handle.close()

    def process_row(self, d, table_name):
        """
        Append row d to the store
        append the list of rows to the HDF5 store and clear the list.
        """

        if len(self._cache) >= MAX_N_ROWS_TO_INSERT:
            self.store_and_clear(table_name)

        self._cache[table_name].append(d)

    def store_and_clear(self, table_name):
        """
        Convert the cache list to a DataFrame and append that to HDF5.
        """

        try:
            df = pd.DataFrame.from_records(self._cache[table_name])[self._columns[table_name]]

        except KeyError as error:
            logger.warning("No data was collected. Did you press the record button?")
            logger.warning(traceback.print_exc())
            logger.warning(self._cache[table_name])
            logger.warning(self._columns[table_name])
            raise error

        except Exception as error:
            logger.warning('There was an error saving the data')
            logger.warning(traceback.print_exc())
            logger.warning(self._cache[table_name])
            logger.warning(self._columns[table_name])
            raise error
        else:
            self._cache.clear()


        # check the dataframe is not empty
        # could be empty if user closes before recording anything

        logger.debug("Saving cache to %s", self._output_csv)

        # save to csv
        try:
            # append data
            with open(self._output_csv, "a") as filehandle:
                df.to_csv(filehandle, header=False)

        except FileNotFoundError:
            logger.warning('File already removed. Not saving cache')

    def save_video(self, frame_anot, frame_orig):


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
