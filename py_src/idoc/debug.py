__author__ = 'quentin'

import numpy as np

class ScanException(BaseException):
    r"""
    A BaseException raised when `~_get_json` fails
    """
    pass


class EthoscopeException(Exception):

    def __init__(self, value, img=None):
        """
        A custom exception. It can store an image

        :param value: A value passed to the exception, generally a text message
        :param img: an image
        :type img: :class:`~numpy.ndarray`
        :return:
        """
        self.value = value
        if isinstance(img, np.ndarray):
            self.img = np.copy(img)
        else:
            self.img = None

    def __str__(self):
        return repr(self.value)

class IDOCException(EthoscopeException):
    r"""
    The same as EthoscopeException but with a name
    fitting for this package
    """
    pass