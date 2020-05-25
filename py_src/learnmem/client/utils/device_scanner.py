# for now it will not scan devices, just retrieve attributes of a device running on localhost

from threading import Thread
import time
import urllib.request
import json
from functools import wraps

import numpy as np

class ScanException(BaseException):
    pass


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
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


class Device():

    _odor_A = "A"
    _odor_B = "B"
    _frame_color = np.array([])
    _program_path = None
    #rsession will run on client
    _r_session = None
    _fps = 0
    _acquisition_time = 0
    _adaptation_time = 0

    _events = {}
    _settings = {}
    _metadata = {}
    _info = {}

    def __init__(self, ip, port=9000):

        self._ip = ip
        self._port = port


    @retry(ScanException, tries=3, delay=1, backoff=1)
    def _get_json(self, url, timeout=5, post_data=None):
        """
        Ethoscope
        """

        try:
            req = urllib.request.Request(url, data=post_data, headers={'Content-Type': 'application/json'})            
            f = urllib.request.urlopen(req, timeout=timeout)
            message = f.read()
            if not message:
                # logging.error("URL error whist scanning url: %s. No message back." % self._id_url)
                raise ScanException("No message back")
            try:
                resp = json.loads(message)
                return resp
            except ValueError:
                # logging.error("Could not parse response from %s as JSON object" % self._id_url)
                raise ScanException("Could not parse Json object")
        
        except urllib.error.HTTPError as e:
            raise ScanException("Error" + str(e.code))
            #return e
        
        except urllib.error.URLError as e:
            raise ScanException("Error" + str(e.reason))
            #return e
        
        except Exception as e:
            raise ScanException("Unexpected error" + str(e))

    def push(self, value, param_name):
        url = f"http://{self._ip}:{self._port}/update"
        self._get_json(url, post_data={"param_name": param_name, "value": value})
       

    def control(self, action):
        url = f"http://{self._ip}:{self._port}/control/{action}"
        self._get_json(url)
       
    def close(self, answer="Y"):

        url = f"http://{self._ip}:{self._port}/close"
        self._get_json(url, post_data={"answer", answer})

    def get_camera_settings(self):

        url = f"http://{self._ip}:{self._port}/camera"
        self._settings = self._get_json(url)
        
    def get_metadata(self):
        url = f"http://{self._ip}:{self._port}/metadata"
        self._metadata = self._get_json(url)

    def get_events(self):
        url = f"http://{self._ip}:{self._port}/events"
        self._events = self._get_json(url)

    def get_programs(self):
        url = f"http.//{self._ip}:{self._port}/list_programs"
        self._programs = self._get_json(url)

    def get_pin_state(self):

        url = f"http.//{self._ip}:{self._port}/pin_state" 
        self._pin_state = self._get_json(url)


    def post_program(self, program_path):

        url = f"http://{self._ip}:{self._port}/load_program"
        self._get_json(url, post_data={"program_path": program_path})

    def _update_info(self):

        # get data
        self.get_camera_settings()
        self.get_metadata()
        self.get_events()
        self.get_programs()
        self.get_pin_state()

        # update info
        self._info.update(self._settings)
        self._info.update(self._metadata)
        self._info.update(self._events)
        self._info.update(self._programs)
        self._info.update(self._pin_state)


    @property
    def info(self):
        return self._info

class DeviceScanner(Thread):

    _devices = []

    def __init__(self, device_refresh_period=5, deviceClass=Device):

        self._device_refresh_period = device_refresh_period
        self._deviceClass = deviceClass
        
    def get_device(self, idx):
        return self._devices[idx]

    def run(self):

        self._devices.append(self._deviceClass(ip="localhost"))

        while True:
            time.sleep(self._device_refresh_period)

            for device in self._devices:
                device._update_info()





        
        