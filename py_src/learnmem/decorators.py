__all__ = []
import functools
import traceback
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def export(defn):
    globals()[defn.__name__] = defn
    __all__.append(defn.__name__)
    return defn

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

# def if_record_event(control_thread):
def if_record_event(f):
    def wrapper(self, *args, **kwargs):
        is_set = self.control_thread.record_event.is_set()
        if not is_set:
            return True            
        return f(self, *args, **kwargs)
    return wrapper
    # return _if_record_event

# def if_record_event(control_thread):
def if_not_record_event(f):
    def wrapper(self, *args, **kwargs):
        is_set = self.control_thread.record_event.is_set()
        if is_set:
            return True            
        return f(self, *args, **kwargs)
    return wrapper
    # return _if_record_event



def if_play_event(f):
    def wrapper(self, *args, **kwargs):
        is_set = self.control_thread.play_event.is_set()
        if not is_set:
            return True            
        return f(self, *args, **kwargs)
    return wrapper
    # return _if_record_event

# def if_record_event(control_thread):
# def if_config_loaded(f):
#     def wrapper(self, *args, **kwargs):
#         config_loaded = not self.control_thread.config is None
#         if not config_loaded:
#             print('config is not loaded')
#             return True            
#         return f(self, *args, **kwargs)
#     return wrapper
    # return _if_record_event


def if_not_record_end_event(f):
    def wrapper(self, *args, **kwargs):
        record_end_set = self.control_thread.record_end.is_set()
        
        if record_end_set:
            if not getattr(self.control_thread, "exit_message_shown", False):
                self.control_thread.getLogger(name='LeMDT.cli_app').info('End of paradigm reached. No recording anymore. Quit to either remove or save the results! :)')
                self.control_thread.getLogger(name='LeMDT.cli_app').info('Press enter to return back to the options menu')
                self.control_thread.exit_message_shown = True
            return True            
        return f(self, *args, **kwargs)
    return wrapper



def if_not_self_stream(f):
    def wrapper(self, *args, **kwargs):
        stream_available = not self.control_thread.tracker.stream is None
        if stream_available:
            print('Skip stream')
            self.log.info(sef.control_thread.tracker.stream)
            return True            
        return f(self, *args, **kwargs)
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

    