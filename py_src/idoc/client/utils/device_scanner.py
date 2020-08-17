# for now it will not scan devices, just retrieve attributes of a device running on localhost
import json
import logging
from threading import Thread
import time
import urllib.error
import urllib.request
import urllib.parse

import requests

from idoc.client.utils.logging_server import LogRecordSocketReceiver
from idoc.client.utils.mixins import HTTPMixin
from idoc.debug import IDOCException, ScanException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



class Device(Thread, HTTPMixin):
    r"""
    Individual Drosophila Optogenetic Conditioner Device
    """
    _remote_pages = {
            'id' : "id",
            # 'videofiles' :  "data/listfiles/video",
            # 'stream' : "stream.mjpg",
            # 'user_options' : "user_options",
            'log' : "data/log",
            'static' : "static",
            'controls' : "controls",
            'logs' : 'logs'
            # 'machine_info' : "machine",
            # 'update' : "update"
            }



    _allowed_instructions_status = { "stream": ["stopped"],
                                     "start": ["stopped"],
                                     "start_record": ["stopped"],
                                     "stop": ["streaming", "running", "recording"],
                                     "poweroff": ["stopped"],
                                     "reboot" : ["stopped"],
                                     "restart" : ["stopped"],
                                     "offline": []}




    def __init__(self, ip, *args, port=9000, remote=False, log_server=False, **kwargs):

        self._ip = ip
        self._port = port
        self._info = {}
        self._settings = {}
        self._id_url = "http://%s:%i/%s" % (ip, port, self._remote_pages['id'])
        self._id = ""
        self._log_server = log_server
        self._remote = remote

        self.running = False
        self.stopped = False

        if self._log_server:
            self._logs_cache = []
            self._tcpserver = LogRecordSocketReceiver()

        super().__init__(*args, **kwargs)

    def get_api(self, api_endpoint, remote=False):

        if api_endpoint is list:
            api_endpoint = "/".join(api_endpoint)


        if self._remote or remote:
            url = "http://%s:%s/device/%s/%s" % (
                self._ip, self._port,
                self.id, api_endpoint
            )

        else:
            url = "http://%s:%s/%s/%s" % (
                self._ip, self._port,
                api_endpoint, self.id
            )

        return url


    def controls(self, submodule, action):

        url = self.get_api([self._remote_pages["controls"], submodule, action])
        return self._get_json(url)

    def close(self, answer="Y"):

        url = self.get_api("close")
        self._get_json(url, post_data={"answer": answer})

    def get_paradigms(self):

        url = self.get_api("list_paradigms")
        return self._get_json(url)

    def post_paradigm(self, paradigm_path):
        """
        :param paradigm_path: A path to a paradigm.csv that IDOC controllers understand
        :type paradigm_path: bytes
        """

        url = self.get_api("load_paradigm")
        # import ipdb; ipdb.set_trace()
        requests.post(url, data=paradigm_path)
        # self._get_json(url, post_data={"paradigm_path": paradigm_path})

    def post_settings(self, settings):
        """
        Post a settings dictionary
        """
        url = self.get_api("settings")
        # import ipdb; ipdb.set_trace()
        self._get_json(url, post_data=json.dumps(settings).encode())


    @property
    def settings(self):
        return self._settings

    @settings.getter
    def settings(self):

        url = self.get_api("settings")
        self._settings = self._get_json(url)
        return self._settings

    def start_experiment(self):
        url = self.get_api("controls/control_thread/start_experiment")
        self._get_json(url)

    def stop_experiment(self):
        url = self.get_api("controls/control_thread/stop_experiment")
        self._get_json(url)

    def reset_experiment(self):
        url = self.get_api("controls/control_thread/reset_experiment")
        self._get_json(url)

    def warm_up(self):
        url = self.get_api("controls/control_thread/warm_up")
        self._get_json(url)

    @property
    def info(self):
        return self._info

    def get_info(self):
        logging.debug('Getting self._info')
        url = self.get_api("info")
        self._info = self._get_json(url)
        logging.debug('_get_json self._info')
        return self._info

    # def get_logs(self):
    #     return self._logs_cache

    # def post_logs(self, post_data):
    #     parsed_data = urllib.parse.parse_qs(post_data.decode())
    #     # print(parsed_data)
    #     self._logs_cache.extend(parsed_data["logs"])


    def _reset_info(self):
        r"""
        This is called whenever the device goes offline or when it is first added
        """
        self._info = {'status': "offline"}

    @property
    def id(self):
        return self._id

    @id.getter
    def id(self):
        r"""
        """
        old_id = self._id
        try:
            resp = self._get_json(self._id_url)
        except ScanException:
            return self._id

        self._id = resp['id']
        if self._id != old_id:
            if old_id:
                logging.info("Device id changed at %s. %s ===> %s", self._ip, old_id, self._id)
            self._reset_info()

        # keep the ip
        self._info["ip"] = self._ip
        return self._id

    def ip(self):
        return self._ip


    def run(self):

        self.running = True

        if self._log_server:
            print('About to start TCP server...')
            self._tcpserver.serve_until_stopped()

        while not self.stopped:
            # Implement here whatever I need
            time.sleep(1)

    def stop(self):

        self.stopped = True
        if self._log_server:
            self._tcpserver.abort = True

    def last_image(self):
        """
        Collects the last drawn image fromt the device
        TODO: on the device side, this should not rely on an actuale image file but be fished from memory
        """
        # we return none if the device is not in a stoppable status (e.g. running, recording)
        if self.info["status"] not in self._allowed_instructions_status["stop"]:
            return None
        try:
            img_path = self.info["recognizer"]["last_annot_path"].lstrip("/")
        except KeyError:
            raise KeyError("Cannot find last image for device %s" % self._id)

        img_url = self.get_api([self._remote_pages['static'], img_path], remote=False)
        # img_url = "http://%s:%i/%s/%s" % (self._ip, self._port, self._remote_pages['static'], img_path)
        try:
            return urllib.request.urlopen(img_url, timeout=5)
        except urllib.error.HTTPError:

            raise Exception("Could not get image for ip = %s (id = %s)" % (self._ip, self._id))


class DeviceScanner(Thread):

    def __init__(self, *args, device_refresh_period=5, deviceClass=Device, remote=False, **kwargs):

        self.devices = []
        self._device_refresh_period = device_refresh_period
        self._deviceClass = deviceClass
        self._remote = remote
        self._max_trials = 50
        self.running = False
        self.stopped = False
        super(DeviceScanner, self).__init__(*args, **kwargs)


    def get_all_devices_info(self):

        '''
        Returns a dictionary in which each entry has key of device_id
        '''
        out = {}

        for device in self.devices:
            out[device.id] = device.info
        return out

    def get_device(self, idx):
        return self.devices[idx]

    def get_device_by_id(self, machine_id, silent=True, trials=0):

        if silent and trials == 0:
            print("Connecting to IDOC device in machine %s" % (machine_id))

        for device in self.devices:
            try:
                info_id = device.info['id']
            except KeyError:
                continue

            if info_id == machine_id:
                return device

        if silent or trials > self._max_trials: # pylint: disable=no-else-return
            trials += 1
            time.sleep(2)
            return self.get_device_by_id(machine_id, trials=trials)

        else:
            message = "Device with machine_id %s is not available." % machine_id
            raise IDOCException(message)

    def run(self):

        self.running = True

        device = self._deviceClass(ip="localhost", remote=self._remote)
        device.start()
        self.devices.append(device)

        while not self.stopped:
            time.sleep(self._device_refresh_period)

            for device in self.devices:
                device.get_info()


    def stop(self):
        for device in self.devices:
            device.stop()

        self.stopped = True