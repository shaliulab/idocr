# Standard library imports
import logging.config
import os

# Third party imports
import yaml
import numpy as np
import coloredlogs
import threading
from decorators import export

class ReadConfigMixin():

    def __init__(self, *args, **kwargs):

        with open(self.interface.config, 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

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

def _toggle_pin(self, device=None, pin_number=None, pin_id=None, value=0, freq=None, thread=True):
    """
    Update the state of pin pin_number with value,
    while logging and caching this so user can confirm it.
    """

    if device is None:
        device = self.device

    if pin_number is None:
        pin_number = device.mapping["pin_number"].loc[device.mapping.index == pin_id].values[0]
        print(pin_number)

    d = threading.currentThread()
    
    # Update state of pin (value = 1 or value = 0)
    device.board.digital[pin_number].write(value)

    # Update log with info severity level unless
    # on pin13, then use severity debug
    if self.log.info:
        f = self.log.info
        
        if thread:
            f("{} - {}".format(
            d._kwargs["d_name"],
            value
            ))
        else:
            f("{} - {}".format(
            pin_id, value
            ))   

    x = value if not freq else freq
    print("x")
    print(x)

    device.pin_state[getattr(self, "pin_name", pin_id)] = x
