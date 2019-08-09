# Standard library imports
import logging.config
from pathlib import Path
import os

# Third party imports
import yaml
import numpy as np
import pandas as pd

from lmdt_utils import setup_logging

setup_logging()

def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)

log = logging.getLogger(__name__)

class PDLoader():

    def __init__(self, mapping_path, program_path):


        self.loaded = False
        self.block_names = None
        self.overview = None
        self.index_col = 'pin_id'
        self.blocks_folder = self.interface.cfg["blocks"]["folder"]
        self.pattern = self.interface.cfg["blocks"]["pattern"]
        
        # Read mapping table (pin coordinates and names)
        mapping = pd.read_csv(mapping_path, skip_blank_lines=True, comment="#")
        mapping.set_index(self.index_col, inplace=True)
        self.mapping = mapping

        # Fetch blocks available in the folder
        # A block is an ensemble of events with a practical function (testing, training, etc)
        blocks = {f.split(".")[0]: f for f in os.listdir(self.blocks_folder) if f.endswith(self.pattern)}
        self.blocks = blocks

        
        # Read program table
        program = pd.read_csv(program_path)
        
        # Make numeric and divide by 60
        program = self.format(program, 'block')
        # Autocomplete start NaNs based on previous block
        program = self.complete_nan(program)  
        # Compute the end for each block
        program["end"] = program["start"] + program["duration"] * program["times"]

        # Take a snapshot of the program and save it in overview
        overview = program
        block_names = overview.index #  commment

        program = self.compile(program, blocks)
        self.overview = overview
        self.program = program
        self.block_names = block_names
        self.loaded = True
        log.info('Paradigm is read')

    def complete_nan(self, program):

        old_start = 0
        for i, row in enumerate(program.itertuples()):
            # Compute what is the start if row.start != row.start (i.e. row.start is np.nan)
            # based on the start, duration and times of the previous (old) block
            start = row.start if row.start == row.start else (old_start+row.duration*row.times)
            program.loc[program.index[i], 'start'] = start
            old_start = start

        return program

    def format(self, df, index):
        df.set_index(index, inplace=True)

        for field in ['start', 'end', 'on', 'off', 'duration']:
            if field in df.columns:
                df[field] = df[field].apply(convert) * 60
        return df

    def read_block(self, block_name):
        block = pd.read_csv(Path(self.blocks_folder, self.blocks[block_name]), skip_blank_lines=True, comment="#")
        block = self.format(block, 'pin_id')
        return block

    def compile(self, program, blocks):
        '''
        Put all the blocks together in a single data frame
        taking into account block repetitions
        Takes the event dataframe contained in the block file
        and the program (block coordinator) contained in the program
        and returns an event dataframe reflecting thestructure in the block coordinator 
        '''

        new_program = [None,] * program.shape[0]
        # For every row in the program file (i.e. every block)
        for i, row in enumerate(program.itertuples()):

            
            # Fetch the fields
            block_name = row.Index
            start = row.start
            times = row.times
            duration = row.duration
            # Read the block and format it the same way the program file was
            block = self.read_block(block_name)

            # Copy the block times times (as instructed in the program csv file)
            block_repeat = pd.concat([block for t in range(times)])
            # Create an itereations column that will contain for each event
            # the iteration of the block it corresponds to 
            iter_column = np.concatenate([np.repeat(t, block.shape[0]) for t in range(times)])
            block_repeat["iterations"] = iter_column
            # If the block is repeated once, then all the events will get 0 in the iterations field
            # If the block is repeated twice, then all the events will be duplicated
            # (first one batch and then the other)
            # and the second batch will have 1 in iterations, and so forth

            # Add block start to all the events in the block
            # as their time is relative to the block start
            # and not the program i.e. actual start 
            block_repeat.loc[:, "start"] += start
            block_repeat.loc[:, "end"] += start
            
            # Add a new column stating what block this events come from
            block_repeat.loc[:, "block"] = block_name                

            # Finally, if there are iterations, we need to add the duration of 1 iterations
            # to the 2nd iteration, 2 durations to the 3rd iteration, and so forth
            block_repeat["start"] = block_repeat["start"] + block_repeat["iterations"] * duration

            # End will be either the one that would correspond based on the number of iterations and the duration
            # unless the block stops earlier than that i.e. the maximum is row.end so we need
            # to take the element-wise minimum of the event ends (end) and the block end (row.end)
            end = (block_repeat["end"] + block_repeat["iterations"] * duration).values
            row_end = np.array([row.end])

            end = np.minimum(row.end, end)
            block_repeat.loc[:, "end"] = end

            # Add the dataframe to the corrresponding position of the dfs list
            new_program[i] = block_repeat

        # Concat all the dataframes in the list and return it
        compiled_program = pd.concat(new_program, sort=True)
        
        return compiled_program