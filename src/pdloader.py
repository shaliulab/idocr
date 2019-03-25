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
        self.index_col = 'pin_id'

        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")

        self.blocks_folder = self.interface.cfg["blocks"]["folder"]
        pattern = self.interface.cfg["blocks"]["pattern"]
        
        blocks = {f.split(".")[0]: f for f in os.listdir(self.blocks_folder) if f.endswith(pattern)}

        mapping.set_index(self.index_col, inplace = True)
        self.mapping = mapping

        program = pd.read_csv(program)
        program = self.format(program, 'block')        
        program = self.compile(program, blocks)
        self.program = program
        
        self.loaded = True
        self.log = logging.getLogger(__name__)
    
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

    def compile(self, program, blocks):

        new_program = [None,] * program.shape[0]
        j = 0
        start = 0
        for row in program.itertuples():

            block = row.Index
            start = row.start if row.start == row.start else (start + duration*times)
            times = row.times
            duration = row.duration

            block_table = self.read_block(blocks[block])

            iter_column = np.concatenate([np.repeat(t, block_table.shape[0]) for t in range(times)])
            block_table_repeat = pd.concat([block_table for t in range(times)])
            block_table_repeat["iterations"] = iter_column

            block_table_repeat.loc[:, "start"] += start
            block_table_repeat.loc[:, "end"] += start

            block_table_repeat["start"] = block_table_repeat["start"] + block_table_repeat["iterations"] * duration
            block_table_repeat["end"] = block_table_repeat["end"] + (1 + block_table_repeat["iterations"]) * duration

            block_table_repeat["block"] = block

                
            new_program[j] = block_table_repeat
            j += 1

        compiled_program = pd.concat(new_program)
        return compiled_program