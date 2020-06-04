# Standard library imports
import logging
import os
import os.path
#import traceback

# Third party imports
import pandas as pd

# Local application imports
# from learnmem.decorators import if_record_event, if_not_record_end_event
from learnmem.configuration import LearnMemConfiguration
from learnmem.helpers import get_machine_id, get_machine_name
from learnmem.server.core.base import Settings, Status, Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

config = LearnMemConfiguration()

class CSVResultWriter(Settings, Status, Root):
    r"""
    Save results to csv files styled in the format:
    start_datetime + '_learnmem_' + self._machine_id + _TABLENAME .csv
    """
    def __init__(self, start_datetime, *args, nrois=20, max_n_rows_to_insert=10, **kwargs):

        super().__init__(*args, **kwargs)
        super().run()

        self._max_n_rows_to_insert = max_n_rows_to_insert
        updated_tables = ["ROI_%d" % i for i in range(1, nrois+1)]
        updated_tables.append("CONTROLLER_EVENTS")
        self._updated_tables = updated_tables
        self._static_tables = ["METADATA", "ROI_MAP", "VAR_MAP"]

        self._tables = self._updated_tables.extend(self._static_tables)
        self._cache = {table: [] for table in self._updated_tables}
        self._start_datetime = start_datetime
        self._root_dir = config.content["folders"]["results"]["path"]

        self._result_dir = os.path.join(
            self._root_dir,
            get_machine_id(),
            get_machine_name(),
            start_datetime
        )
        print(self._result_dir)

        logger.debug('Output will be saved in %s', self._result_dir)
        os.makedirs(self._result_dir, exist_ok=False)

        self._prefix = start_datetime + '_idoc_' + get_machine_id()
        self._output_csv = os.path.join(self._result_dir, self._prefix + ".csv")
        self._metadata = None

    @property
    def result_dir(self):
        return self._result_dir

    def save_metadata(self, metadata):
        self._metadata = metadata
        path2file = os.path.join(self._result_dir, "metadata.csv")
        metadata.to_csv(path2file)


    def write(self, t_ms, roi, data_rows):
        """
        An adaptor for the DataPoint instances to be compatible
        with process_row
        """
        t_ms = int(round(t_ms))
        table_name = "ROI_%d" % roi.idx

        for row in data_rows:
            data_points = {**{"id": 0, "t_ms": t_ms}, **{v.header_name: v for v in row.values()}}
            self.process_row(data_points, table_name)


    def process_row(self, data, table_name):
        """
        Store a new controller event
        """
        data = {k.strip(" "): data[k] for k in data}

        if self.running and not self.stopped:
            if len(self._cache[table_name]) >= self._max_n_rows_to_insert:
                self.store_and_clear(table_name)
            self._cache[table_name].append(data)

    def get_table_path(self, table_name):
        filename = "%s_%s.csv" % (self._prefix, table_name.upper())
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
