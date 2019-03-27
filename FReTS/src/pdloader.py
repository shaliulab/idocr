# Standard library imports
import logging.config
from pathlib import Path
import os

# Third party imports
import yaml
import numpy as np
import pandas as pd

from frets_utils import setup_logging

setup_logging()

def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)


class PDLoader():

    def __init__(self, mapping, program):
        self.loaded = False
        self.block_names = None
        self.overview = None

        self.index_col = 'pin_id'

        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")

        self.blocks_folder = self.interface.cfg["blocks"]["folder"]
        pattern = self.interface.cfg["blocks"]["pattern"]
        
        blocks = {f.split(".")[0]: f for f in os.listdir(self.blocks_folder) if f.endswith(pattern)}

        mapping.set_index(self.index_col, inplace = True)
        self.mapping = mapping

        program = pd.read_csv(program)
        self.block_names = program['block']

        program = self.format(program, 'block')
        program = self.complete_nan(program)  
        program["end"] = program["start"] + program["duration"] * program["times"]

        self.overview = program
        program = self.compile(blocks)
        self.program = program
        self.loaded = True
        self.log = logging.getLogger(__name__)

    def complete_nan(self, program):
        overview = program
        old_start = 0
        for i, row in enumerate(program.itertuples()):
            print(i)
             # Compute what is the start if row.start != row.start (i.e. row.start is np.nan)
            # based on the start, duration and times of the previous (old) block
            start = row.start if row.start == row.start else (old_start+row.duration*row.times)
            overview.loc[overview.index[i], 'start'] = start
            old_start = start
            
        
        return overview

    
    def format(self, df, index):
        df.set_index(index, inplace=True)

        for field in ['start', 'end', 'on', 'off', 'duration']:
            if field in df.columns:
                df[field] = df[field].apply(convert) * 60
        return df

    def read_block(self, filename):
        block = pd.read_csv(Path(self.blocks_folder, filename), skip_blank_lines=True, comment="#")
        block = self.format(block, 'pin_id')
        return block

    def compile(self, blocks):

        new_program = [None,] * self.overview.shape[0]
        for i, row in enumerate(self.overview.itertuples()):
            print(row)

            block = row.Index
            # Compute what is the start if row.start != row.start (i.e. row.start is np.nan)
            # based on the start, duration and times of the previous (old) block
            start = row.start
            times = row.times
            duration = row.duration

            block_table = self.read_block(blocks[block])

            iter_column = np.concatenate([np.repeat(t, block_table.shape[0]) for t in range(times)])
            block_table_repeat = pd.concat([block_table for t in range(times)])
            block_table_repeat["iterations"] = iter_column

            block_table_repeat.loc[:, "start"] += start
            block_table_repeat.loc[:, "end"] += start

            block_table_repeat["start"] = block_table_repeat["start"] + block_table_repeat["iterations"] * duration
            end = (block_table_repeat["end"] + (1 + block_table_repeat["iterations"]) * duration).values
            
            row_end = np.array([row.end], np.float64)
            end = min(row_end, end)

            
            block_table_repeat.loc[:, "end"] = end
            block_table_repeat.loc[:, "block"] = block


                
            new_program[i] = block_table_repeat

        compiled_program = pd.concat(new_program)
        
        print(compiled_program)
        return compiled_program