# Standard library imports
import logging.config
import os

# Third party imports
import yaml
import numpy as np
import pandas as pd
import coloredlogs

from decorators import export

class ReadConfigMixin():

    def __init__(self, *args, **kwargs):

        with open(self.interface.config, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

        self.cfg = cfg
        #super().__init__(*args, **kwargs)

 
def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)

@export
def setup_logging(
    default_path='logging.yaml',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration

    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

    coloredlogs.install()

setup_logging()
log = logging.getLogger(__name__)

class PDReader():

    def __init__(self, mapping, program, blocks=None):
        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")
        program = pd.read_csv(program, skip_blank_lines=True, comment="#")
        
        blocks = pd.read_csv(blocks)

        mapping.set_index('pin_id', inplace = True)
        program.set_index(['pin_id', 'block'], inplace = True)
        blocks.set_index('block', inplace = True)
        self.mapping = mapping

        self.format(program)
        if blocks is not None:
            self.make_blocks(program, blocks)

    def format(self, program):

        program['start'] = program['start'].apply(convert)
        program['end'] = program['end'].apply(convert)
        program['on'] = program['on'].apply(convert)
        program['off'] = program['off'].apply(convert)
        program *= 60
        self.program = program
    
    def make_blocks(self, program, blocks):

        blocks['start'] = blocks['start'].apply(convert)
        blocks["start"]  *= 60
        blocks['duration'] = blocks['duration'].apply(convert)
        blocks["duration"]  *= 60

        new_program = [None,] * blocks.shape[0]
        j = 0
        for row in blocks.itertuples():
            pb = None
            self.log.info("New iter")
            self.log.info(row)
            block = row.Index
            start = row.start
            times = row.times
            #duration =  max(program_block["end"]) - min(program_block["start"])
            duration = row.duration

            program_block = program.loc[program.index.get_level_values('block') == block]
            #import ipdb; ipdb.set_trace()
            program_block.loc[:, "start"] += start
            pb = [None,] * times
            iter_column = np.concatenate([np.repeat(t, program_block.shape[0]) for t in range(times)])
            program_block = pd.concat([program_block for t in range(times)])
            program_block["iterations"] = iter_column

            program_block["start"] = program_block["start"] + program_block["iterations"] * duration

                
            new_program[j] = program_block
            j += 1

        df = pd.concat(new_program)
        self.program = df
        print(self.program)
