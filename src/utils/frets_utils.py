# Standard library imports
import logging.config
import os

# Third party imports
import yaml
import numpy as np
import pandas as pd
import coloredlogs

def mixedomatic(cls):
    """ Mixed-in class decorator. """
    classinit = cls.__dict__.get('__init__')  # Possibly None.
    bases = [e for e in cls.__bases__ if e.__name__[-5:] == "Mixin"]

    # Define an __init__ function for the class.
    def __init__(self, *args, **kwargs):
        # Call the __init__ functions of all the bases.
        for base in bases:
            base.__init__(self, *args, **kwargs)
        # Also call any __init__ function that was in the class.
        if classinit:
            classinit(self, *args, **kwargs)

        for base in bases:
            __init2__ = base.__dict__.get('__init2__')
            if __init2__:
                __init2__(self, *args, **kwargs)

    # Make the local function the class's __init__.
    setattr(cls, '__init__', __init__)
    return cls

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



class PDReader():

    def __init__(self, mapping, program):
        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")
        program = pd.read_csv(program, skip_blank_lines=True, comment="#")
        mapping = mapping.set_index('pin_id')
        program = program.set_index('pin_id')
        program['start'] = program['start'].apply(convert)
        program['end'] = program['end'].apply(convert)
        program['on'] = program['on'].apply(convert)
        program['off'] = program['off'].apply(convert)
        
        program = program * 60

        self.mapping = mapping
        self.program = program 