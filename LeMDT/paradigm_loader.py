# Standard library imports
import logging.config
from pathlib import Path
import os

# Third party imports
import yaml
import numpy as np
import pandas as pd


def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)

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
            self.log.error("Inheriting class of ParadigmLoader does not have an interface attribute")
            raise Exception

        # Loaded becomes true when __init__ is finished
        self.loaded = False

        ###########################################################################
        # LINK BLOCKS
        # A dictionary mapping a block name to its csv file
        ###########################################################################

        # Define a string pattern that will be matched to filenames
        pattern = self.interface.cfg["blocks"]["pattern"]
        # Fetch blocks available (filenames in the folder without the extension)
        # A block is an ensemble of events with a practical function eg. testing, conditioning,
        self.program_path = program_path
        programs_folder = os.path.dirname(self.program_path)
        self.blocks_folder = os.path.join(programs_folder, '..', 'blocks')
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
        # block,start,times
        # clean,0,1

        program = pd.read_csv(program_path)       
        program.set_index('block')

        # Format time in seconds
        program = self.minutes_to_seconds(program)
        # Autocomplete start NaNs based on previous block
        program = self.infer_block_start_from_previous_block(program)  
        # Infer the end for each block
        # program["end"] = program["start"] + program["duration"] * program["times"]

        self.program = program

        
        # Take a snapshot of the program and save it in overview
        # overview = program
        # block_names = overview.index #  commment

        self.paradigm = self.compile(self.program, self.blocks)
        # self.overview = overview
        # self.block_names = block_names
        self.loaded = True
        self.log.info('Paradigm is read')

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
        block.set_index('pin_id')
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
        block_ends = np.array([None,] * program.shape[0])
        # For every block in the program file
        max_end = 0
        for i, block_row in enumerate(program.itertuples()):
            
            # Fetch the needed fields
            block_name = block_row.block # the block name
            start = block_row.start
            times = block_row.times
            # duration = block_row.duration
            

            # Read the block and format it the same way the program file was
            block = self.read_block(block_name)
            block = self.minutes_to_seconds(block)
            
            x = np.array([0], dtype=np.float64)
            y = block['end'].values
            
            
            # print(times)

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
            
            # Add a new column stating what block this events come from
            block_repeat.loc[:, "block"] = block_name                



            if block_name != 'startup':

                # import ipdb; ipdb.set_trace()

                DURATION = max(x, max(y))

                # print('start')
                # print(start)
                
                # add the start of the block (from the program file) to the ends
                block_repeat.loc[:, "end"] += start
                # if there are iterations, add the durations of the block

                # Finally, if there are iterations, we need to add the duration of 1 iterations
                # to the 2nd iteration, 2 durations to the 3rd iteration, and so forth
                block_repeat["start"] = block_repeat["start"] + block_repeat["iterations"] * DURATION

                # End will be either the one that would correspond based on the number of iterations and the duration
                # unless the block stops earlier than that i.e. the minimum is block.end so we need
                # to take the element-wise minimum of the event ends (end) and the block end (block.end)
                end_column = (block_repeat["end"] + block_repeat["iterations"] * DURATION).values
                # print(block_name)
                # print(end_column)
                

                block_end = np.array([block.end])

                # end_column_corrected = np.minimum(block_end, end_column).T
                block_end = np.max(end_column)
                # print('block_name')
                # print(block_name)

                # print('block_end')
                # print(block_end)

                max_end = max(int(block_end), int(max_end))
                self.interface.duration = max_end
                # print('max_end')
                # print(max_end)

                
            else:
                status_end = max_end
                end_column_corrected = np.array([status_end for i in range(block_repeat.shape[0])])
                block_repeat.loc[:, "end"] = end_column_corrected


            # Add the dataframe to the corrresponding position of the expanded_blocks list
            expanded_blocks[i] = block_repeat
            block_ends[i] = block_end

        # Concat all the dataframes in the list and return it
        program['end'] = 0
        for i, block_name in enumerate(program['block']):
            # print(block_name)
            program.at[block_name, 'end'] = block_ends[i]
        self.program = program

        paradigm = pd.concat(expanded_blocks, sort=True)
        # paradigm.set_index('pin_id', inplace=True)
        paradigm.reset_index(inplace=True, drop='index')

        # print(paradigm.index)

        # Initialize the active and thread_name columns with default values
        # active will serve as a dynamic monitor
        # thread_name will be filled in this function
        paradigm["active"] = False
        paradigm["thread_name"] = None
        # print(paradigm)
        return paradigm