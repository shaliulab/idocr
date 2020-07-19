# Standard library imports
import logging
import os
import os.path
#import traceback

# Third party imports
import cv2
import pandas as pd

# Local application imports
# from idoc.decorators import if_record_event, if_not_record_end_event
from idoc.configuration import IDOCConfiguration
from idoc.helpers import get_machine_id, get_machine_name
from idoc.server.core.base import Settings, Status, Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

config = IDOCConfiguration()

class CSVResultWriter(Settings, Status, Root):
    r"""
    Save results to csv files styled in the format:
    start_datetime + '_idoc_' + self._machine_id + _TABLENAME .csv
    """

    _quality = cv2.IMWRITE_JPEG_QUALITY

    def __init__(self, *args, nrois=20, max_n_rows_to_insert=10, **kwargs):

        super().__init__(*args, **kwargs)

        self._max_n_rows_to_insert = max_n_rows_to_insert
        updated_tables = ["ROI_%d" % i for i in range(1, nrois+1)]
        updated_tables.append("CONTROLLER_EVENTS")
        self._updated_tables = updated_tables
        self._static_tables = ["METADATA", "ROI_MAP", "VAR_MAP"]

        self._tables = self._updated_tables.extend(self._static_tables)
        self._cache = {table: [] for table in self._updated_tables}
        self._root_dir = config.content["folders"]["results"]["path"]
        self._machine_id = get_machine_id()

        self._var_map_initialised = False
        self._metadata_initialised = False
        self._roi_map_initialised = False
        self.last_t = None

        self.start_datetime = ""
        self._result_dir = ""
        self._output_csv = None
        self._run_id_long = None


    @property
    def info(self):
        return {
            "result_dir": self.result_dir
        }

    @property
    def run_id_long(self):
        self._run_id_long = "%s_%s" % (self.start_datetime, self._machine_id)
        return self._run_id_long


    @property
    def result_dir(self):

        if self.running:
            logger.debug('Output will be saved in %s', self._result_dir)

            self._result_dir = os.path.join(
                # self._root_dir,
                # self._machine_id,
                # get_machine_name(),
                "/tmp",
                self.start_datetime
            )

        else:
            self._result_dir = ""

        return self._result_dir

    @property
    def img_snapshots(self):
        return os.path.join(
            self.result_dir,
            "IMG_SNAPSHOTS"
        )

    @property
    def snapshots_template(self):
        return os.path.join(
            self.img_snapshots,
            "FRAME_%s.jpg"
        )

    @property
    def output_csv(self):
        self._output_csv = os.path.join(self.result_dir, self.run_id_long + ".csv")


    def set_running(self):

        self.running = True

        try:
            os.makedirs(self.result_dir, exist_ok=False)
        except FileExistsError:
            logger.warning('Output directory already exists. This is weird. Are you passing a custom start_datetime?')
            logger.warning(self.result_dir)



    def initialise_metadata(self, metadata):

        if not self._metadata_initialised:
            metadata.to_csv(
                os.path.join(
                    self._result_dir,
                    self.run_id_long + "_METADATA.csv"
                )
            )

            self._metadata_initialised = True

    def initialise_roi_map(self, rois):

        if not self._roi_map_initialised:

            roi_map = []

            for roi in rois:
                roi_map.append(roi.get_feature_dict())

            roi_map_df = pd.DataFrame(roi_map)
            roi_map_df.to_csv(
                os.path.join(
                    self._result_dir,
                    self.run_id_long + "_ROI_MAP.csv"
                )
            )
            self._roi_map_initialised = True




    def initialise_var_map(self, data_rows):
        """
        Store the name of the columns and their functional type in a separate table
        """

        var_map = []

        for data in data_rows.values():
            try:
                var_map.append({
                    "var_name": data.header_name,
                    "sql_type": data.sql_data_type,
                    "functional_type": data.functional_type
                })
            except AttributeError as error:
                logger.warning(error)
                logger.warning(data)


        var_map_df = pd.DataFrame(var_map)
        var_map_df.to_csv(
            os.path.join(
                self._result_dir,
                self.run_id_long  + "_VAR_MAP.csv"
            )
        )

        self._var_map_initialised = True

    def write(self, roi, data_rows):
        """
        An adaptor for the DataPoint instances to be compatible
        with process_row
        """
        if self.running:

            if not self._var_map_initialised:
                self.initialise_var_map(data_rows[0])

            table_name = "ROI_%d" % roi.idx
            for row in data_rows:
                data_points = {**{"id": 0}, **{v.header_name: v for v in row.values()}}
            self.process_row(data_points, table_name)


    def write_frames(self, img, idx):

        if not os.path.isdir(self.img_snapshots):
            os.makedirs(self.img_snapshots)

        cv2.imwrite(self.snapshots_template % str(idx).zfill(7), img, [int(self._quality), 50])


    def process_row(self, data, table_name):
        """
        Store a new data point only if running and not stopped.
        """

        if self.running and not self.stopped:
            data = {k.strip(" "): data[k] for k in data}

            data.update({"t": self.last_t})
            data.update({"elapsed_seconds": self.elapsed_seconds})

            self._cache[table_name].append(data)

            # if table_name == "CONTROLLER_EVENTS":
            #     print(self._cache[table_name])
            if len(self._cache[table_name]) >= self._max_n_rows_to_insert:
                self.store_and_clear(table_name)

    def get_table_path(self, table_name):
        """
        Generate the absolute path to one of the tables
        generated in the output.
        """
        filename = "%s_%s.csv" % (self.run_id_long, table_name.upper())
        table_path = os.path.join(self._result_dir, filename)
        return table_path

    def store_and_clear(self, table_name):
        """
        Convert the cache list to a DataFrame and append that to HDF5.
        """

        table_path = self.get_table_path(table_name)

        # Generate a pandas dataframe from the cached list
        records = pd.DataFrame.from_records(self._cache[table_name])

        # Append the generated dataframe to the result_file
        if os.path.exists(table_path):
            mode = "a"
            header = False
        else:
            mode = "w"
            header = True

        # Write the cache to disk in a csv file
        # if table_name == "CONTROLLER_EVENTS":
        #     print(records)
        records.to_csv(table_path, mode=mode, header=header)
        # Once the cache has been written to disk,
        # clear it from RAM
        self._cache[table_name].clear()


    def clear(self):
        """
        Emtpy the cache of all the tables.
        """
        self.stopped = True
        for table in self._cache:
            self.store_and_clear(table)

        self.reset()
