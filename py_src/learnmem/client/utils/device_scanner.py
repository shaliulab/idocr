# for now it will not scan devices, just retrieve attributes of a device running on localhost

import logging
from threading import Thread
import time
import urllib.error, urllib.request

import requests


from learnmem.client.utils.logging_server import LogRecordSocketReceiver
from learnmem.client.utils.mixins import HTTPMixin

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

    def __init__(self, ip, *args, port=9000, **kwargs):

        self._ip = ip
        self._port = port
        self._info = {}
        self._settings = {}
        self._id_url = "http://%s:%i/%s" % (ip, port, self._remote_pages['id'])
        self._id = ""
        self._logs_cache = {"logs": []}
        self._tcpserver = LogRecordSocketReceiver()
        super().__init__(*args, **kwargs)

    def controls(self, submodule, action):
        template = "http://%s:%d/%s/%s/%s/%s"
        url = template % (
            self._ip, self._port,
            self._remote_pages["controls"],
            submodule, action, self.id
        )

        return self._get_json(url)

    def close(self, answer="Y"):

        url = "http://%s:%d/close/%s" % self._ip, self._port, self.id
        self._get_json(url, post_data={"answer": answer})

    # def get_metadata(self):
    #     url = f"http://{self._ip}:{self._port}/metadata"
    #     self._metadata = self._get_json(url)

    def get_programs(self):
        url = f"http.//{self._ip}:{self._port}/list_programs/%s" % self.id
        return self._get_json(url)

    def post_program(self, program_path):

        url = f"http://{self._ip}:{self._port}/load_program/%s" % self.id
        requests.post(url, data={"program_path": program_path})
        # self._get_json(url, post_data={"program_path": program_path})

    def post(self, data):
        url = f"http://{self._ip}:{self._port}/settings/%s" % self.id
        self._get_json(url, post_data=data)

    @property
    def settings(self):
        return self._settings

    @settings.getter
    def settings(self):
        url = f"http://{self._ip}:{self._port}/settings/%s" % self.id
        self._settings = self._get_json(url)


    @property
    def info(self):
        return self._info

    def get_info(self):
        logging.info('Getting self._info')
        url = "http://%s:%d/info/%s" % (self._ip, self._port, self.id)
        self._info = self._get_json(url)
        logging.info('_get_json self._info')
        return self._info

    def get_logs(self):
        return self._logs_cache

    def post_logs(self, post_data):

        # print("CACHE")
        # print(self._logs_cache)
        # print("INCOMING")
        # print(post_data["logs"])
        self._logs_cache["logs"].append(post_data["logs"])
        return {"status": "success"}


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
        resp = self._get_json(self._id_url)
        self._id = resp['id']
        if self._id != old_id:
            if old_id:
                logging.warning("Device id changed at %s. %s ===> %s", self._ip, old_id, self._id)
            self._reset_info()

        # keep the ip
        self._info["ip"] = self._ip
        return self._id

    def ip(self):
        return self._ip


    def run(self):

        print('About to start TCP server...')
        self._tcpserver.serve_until_stopped()

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

        img_url = "http://%s:%i/%s/%s" % (self._ip, self._port, self._remote_pages['static'], img_path)
        try:
            return urllib.request.urlopen(img_url, timeout=5)
        except urllib.error.HTTPError:

            raise Exception("Could not get image for ip = %s (id = %s)" % (self._ip, self._id))


class DeviceScanner(Thread):


    def __init__(self, *args, device_refresh_period=5, deviceClass=Device, **kwargs):

        self.devices = []
        self._device_refresh_period = device_refresh_period
        self._deviceClass = deviceClass
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



    def get_device_by_id(self, machine_id):

        for device in self.devices:
            try:
                info_id = device.info['id']
            except KeyError:
                continue

            if info_id == machine_id:
                return device

        message = "Device with machine_id %s is not available." % machine_id
        logging.warning("DEVICES")
        logging.warning(self.devices)
        raise Exception(message)

    def run(self):

        device = self._deviceClass(ip="localhost")
        device.start()
        self.devices.append(device)

        while True:
            time.sleep(self._device_refresh_period)

            for device in self.devices:
                device.get_info()

