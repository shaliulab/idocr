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

class ParadigmLoader():
    """A class to provide paradigm creation functionality to other classes by inheritance
       Functionality is given by running its init method with a mapping and program path
       that should lead to the corresponding csv files.

    """
    
    def __init__(self, mapping_path, program_path):


        # The inheriting class provides an interface attribute
        if getattr(self, "interface", False):
            self.interface = self.interface
        else:
            log.error("Inheriting class of ParadigmLoader does not have an interface attribute")
            raise Exception

        # Loaded becomes true when __init__ is finished
        self.loaded = False

        ###########################################################################
        # LINK BLOCKS
        # A dictionary mapping a block name to its csv file
        ###########################################################################

        # Read what is the block folder
        self.blocks_folder = self.interface.cfg["blocks"]["folder"]
        # Define a string pattern that will be matched to filenames
        pattern = self.interface.cfg["blocks"]["pattern"]
        # Fetch blocks available (filenames in the folder without the extension)
        # A block is an ensemble of events with a practical function eg. testing, conditioning,
        self.blocks = {f.split(".")[0]: f for f in os.listdir(self.blocks_folder) if f.endswith(pattern)}
                
        ###########################################################################
        # READ MAPPING
        # A csv file encoding pin numbers and names and binding them together
        ###########################################################################
        
        # Should look like this
        # pin_id,pin_number,pin_group,x,y
        # ONBOARD_LED,13,NaN,1,5

        self.mapping = pd.read_csv(mapping_path, skip_blank_lines=True, comment="#")
        self.mapping.set_index('pin_id', inplace=True)
        

        
        ###########################################################################
        # READ PROGRAM
        # A program is an ensemble of blocks put together in a meaningful way
        # e.g. test -> conditioning -> test
        ###########################################################################
        
        # Should look like this
        # block,start,duration,times
        # clean,0,240,1

        program = pd.read_csv(program_path)       
        program.set_index('block')

        # Format time in seconds
        program = self.minutes_to_seconds(program)
        # Autocomplete start NaNs based on previous block
        program = self.infer_block_start_from_previous_block(program)  
        # Infer the end for each block
        program["end"] = program["start"] + program["duration"] * program["times"]
        
        self.program = program
        
        # Take a snapshot of the program and save it in overview
        # overview = program
        # block_names = overview.index #  commment

        self.paradigm = self.compile(self.program, self.blocks)
        # self.overview = overview
        # self.block_names = block_names
        self.loaded = True
        log.info('Paradigm is read')

    def infer_block_start_from_previous_block(self, program):
        """Infer the start field of a block if NaN is given by assuming it follows right after the previous block."""
        previous_start = 0
        for i, block in enumerate(program.itertuples()):
            # Compute what is the start if block.start != block.start (i.e. block.start is np.nan)
            # based on the start, duration and times of the previous (old) block
            start = block.start if block.start == block.start else (previous_start+block.duration*block.times)
            program.loc[program.index[i], 'start'] = start
            previous_start = start

        return program

    def minutes_to_seconds(self, df):
        """Change the unit of the fields containing time in minutes to seconds."""
        for field in ['start', 'end', 'on', 'off', 'duration']:
            if field in df.columns:
                df[field] = df[field].apply(convert) * 60
        return df

    def read_block(self, block_name):
        """Read the correct block file ignoring comments and blank lines."""
        block = pd.read_csv(Path(self.blocks_folder, self.blocks[block_name]), skip_blank_lines=True, comment="#")
        return block

    def compile(self, program, blocks):
        """
        Put all the blocks together in a single data frame taking into account block repetitions.

        Takes the event dataframe (block file).
        and the program i.e. block manager (program file) and returns a paradigm.
        A paradigm consists of all the blocks mentioned in the program put together,
        taking into account the starting times i.e. the structure given by the program.

        Parameters
        ----------

        program: pandas.DataFrame
            Table with fields block, start, duration and times
            The content of the block should map to the name of a block file without .csv

        """

        expanded_blocks = [None,] * program.shape[0]
        # For every block in the program file 
        for i, block in enumerate(program.itertuples()):
            
            # Fetch the needed fields
            block_name = block.Index # the block name
            start = block.start
            times = block.times
            duration = block.duration

            # Read the block and format it the same way the program file was
            block = self.read_block(block_name)
            block.set_index('pin_id')
            block = self.minutes_to_seconds(block)

            # The program describes how many times a block has to be repeated.
            # This line implements this repetition
            block_repeat = pd.concat([block for t in range(times)])

            # Create an itereations column that will contain for each event in the block
            # the repetition of the block it corresponds to 
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
            # unless the block stops earlier than that i.e. the minimum is block.end so we need
            # to take the element-wise minimum of the event ends (end) and the block end (block.end)
            end = (block_repeat["end"] + block_repeat["iterations"] * duration).values
            block_end = np.array([block.end])
            end = np.minimum(block_end, end)
            block_repeat.loc[:, "end"] = end

            # Add the dataframe to the corrresponding position of the expanded_blocks list
            expanded_blocks[i] = block_repeat

        # Concat all the dataframes in the list and return it
        paradigm = pd.concat(expanded_blocks, sort=True)
        
        return paradigm