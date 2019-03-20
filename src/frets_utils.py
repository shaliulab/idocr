import threading
import yaml
import numpy as np

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

        with open(kwargs["config"], 'r') as ymlfile:
            cfg = yaml.load(ymlfile)

        self.cfg = cfg
        #super().__init__(*args, **kwargs)

class MyThread(threading.Thread):
    def start(self, program_start, total_time):
        """
        Extend the start method in threading.Thread() to receive 2 more args, program_start and total_time

        """
        self._kwargs["program_start"] = program_start
        self._kwargs["total_time"] = total_time 
        super(MyThread, self).start()

def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)