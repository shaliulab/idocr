# Standard library imports
import logging.config
import os

# Third party imports
import yaml
import numpy as np
import coloredlogs

from decorators import export

class ReadConfigMixin():

    def __init__(self, *args, **kwargs):

        with open(self.interface.config, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

        self.cfg = cfg
        #super().__init__(*args, **kwargs)

 

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