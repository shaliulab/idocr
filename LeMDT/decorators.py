__all__ = []
import functools

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

def if_record_event(func=None, *, interface=None):
    """Decorator function with arguments
    Decorator can be used with or without arguments
    Examples:
        >>>
        >>> @decorator_with_args
        >>> def func():
        >>>     pass
        >>>
        >>> @decorator_with_args(arg='foo')
        >>> def func():
        >>>     pass
        >>>
    """

    # 1. Decorator arguments are applied to itself as partial arguments
    if func is None:
        return functools.partial(if_record_event, interface=None)

    # 2. logic with the arguments
    ...

    # 3. Handles the actual decorating
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Write decorator function logic here
        # Before function call
        # ...
        if interface.record_event.is_set():
            result = func(*args, **kwargs)
            # After function call
            # ...
            return result
    return wrapper

