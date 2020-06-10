from functools import wraps
import logging
import time
import traceback

from idoc.helpers import get_machine_id


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

id = get_machine_id()

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


class WrongMachineID(Exception):
    r"""
    An exception to be raised when the id
    parsed from the requested URL
    does not match that of the local machine
    """
    pass

def wrong_id(f):
    def wrapper(**kwargs):
        if kwargs["id"] != id:
            raise WrongMachineID
        else:
            if "id" in f.__code__.co_varnames:
                return f(**kwargs)
            else:
                kwargs.pop('id')
                return f(**kwargs)

    return wrapper


def error_decorator(func):
    """
    A simple decorator to return an error dict so we can display it in the webUI
    """
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(traceback.format_exc())
            return {'error': traceback.format_exc()}
    return func_wrapper

def warning_decorator(func):
    """
    A simple decorator to return an error dict so we can display it in the webUI
    Less verbose than error
    """
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(traceback.format_exc())
            return {'error': str(e)}
    return func_wrapper


def retry(ExceptionToCheck, tries=1, delay=1, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry