import argparse
import datetime
import logging
import os
import signal
import subprocess
import sys
import time
import urllib.parse

import bottle
import netifaces

from learnmem.client.utils.device_scanner import DeviceScanner
from learnmem.configuration import LearnMemConfiguration
from learnmem.decorators import warning_decorator, error_decorator
from learnmem.helpers import get_server

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

logging.basicConfig(
    format='%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s'
)



app = bottle.Bottle()
STATIC_DIR = "../../static"



ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port", type=int, default=80)
ap.add_argument("-D", "--debug", action='store_true', dest="debug")
ARGS = vars(ap.parse_args())
CFG = LearnMemConfiguration()

PORT = ARGS["port"]
DEBUG = ARGS["debug"]

logger.info("Running client on port %d", PORT)

ds = DeviceScanner()
ds.start()


@app.route('/')
def index():
    return bottle.static_file('index.html', root=STATIC_DIR)


@app.route('/static/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root=STATIC_DIR)

@app.get('/favicon.ico')
def get_favicon():
    return server_static(STATIC_DIR+'/img/favicon.ico')


@app.get('/devices')
@error_decorator
def devices():
    return ds.get_all_devices_info()


@app.get('/device/<id>')
def get_device_by_id(id):
    return {"id": ds.get_device_by_id(id).info["id"]}



@app.get('/idoc/<id>')
def redirection_to_idoc(id):
    return bottle.redirect('/#/idoc/'+id)


@app.get('/device/<id>/info')
def info(id):
    return ds.get_device_by_id(id).info

@app.get('/device/<id>/controls/<module>/<action>')
def device_actions(id, submodule, action):
    # supported actions:
    return ds.get_device_by_id(id).controls(submodule, action)


@app.post('/device/<id>/settings')
def post_settings(id):
    post_data = bottle.request.body.read()
    return ds.get_device_by_id(id).post(post_data)


@app.get('/device/<id>/settings')
def get_settings(id):
    return ds.get_device_by_id(id).settings

@app.get('/device/<id>/get_logs')
def get_logs(id):
    logs = ds.get_device_by_id(id).get_logs()
    return logs


@app.post('/device/<id>/post_logs')
def post_logs(id):
    post_data = bottle.request.body.read()
    post_data = urllib.parse.parse_qs(post_data.decode())

    if post_data is None:
        result = {"status": "failure"}
    else:
        result = ds.get_device_by_id(id).post_logs(post_data)

    return result


@app.get('/device/<id>/list_programs')
def get_programs(id):
    programs = ds.get_device_by_id(id).get_programs()
    return programs


@app.post('/device/<id>/load_program')
def load_program(id):
    post_data = bottle.request.body.read()
    post_data = urllib.parse.parse_qs(post_data.decode())
    program_path = post_data["program_path"][0]
    print("LOAD PROGRAM")
    print(program_path)


    if post_data is None:
        result = {"status": "failure"}
    else:
        result = ds.get_device_by_id(id).post_program(program_path)

    return result


@app.get('/client/<req>')
@error_decorator
def client_info(req):#, device):
    if req == 'info':

        with os.popen('df %s -h' % RESULTS_DIR) as df:
            disk_free = df.read()

        disk_usage = RESULTS_DIR+" Not Found on disk"

        CARDS = {}
        IPs = []

        CFG.load()

        try:
            disk_usage = disk_free.split("\n")[1].split()

            #the following returns something like this: [['eno1', 'ec:b1:d7:66:2e:3a', '192.168.1.1'], ['enp0s20u12', '74:da:38:49:f8:2a', '155.198.232.206']]
            adapters_list = [ [i, netifaces.ifaddresses(i)[17][0]['addr'], netifaces.ifaddresses(i)[2][0]['addr']] for i in netifaces.interfaces() if 17 in netifaces.ifaddresses(i) and 2 in netifaces.ifaddresses(i) and netifaces.ifaddresses(i)[17][0]['addr'] != '00:00:00:00:00:00' ]
            for ad in adapters_list:
                CARDS [ ad[0] ] = {'MAC' : ad[1], 'IP' : ad[2]}
                IPs.append (ad[2])


            with os.popen('git rev-parse --abbrev-ref HEAD') as df:
                GIT_BRANCH = df.read() or "Not detected"
            #df = subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stdout=subprocess.PIPE)
            #GIT_BRANCH = df.communicate()[0].decode('utf-8')

            with os.popen('git status -s -uno') as df:
                NEEDS_UPDATE = df.read() != ""

            #df = subprocess.Popen(['git', 'status', '-s', '-uno'], stdout=subprocess.PIPE)
            #NEEDS_UPDATE = df.communicate()[0].decode('utf-8') != ""

            with os.popen('systemctl status ethoscope_node.service') as df:
                try:
                    ACTIVE_SINCE = df.read().split("\n")[2]
                except:
                    ACTIVE_SINCE = "Not running through systemd"

        except Exception as e:
            logger.error(e)

        return {'active_since': ACTIVE_SINCE, 'disk_usage': disk_usage, 'IPs' : IPs , 'CARDS': CARDS, 'GIT_BRANCH': GIT_BRANCH, 'NEEDS_UPDATE': NEEDS_UPDATE}

    elif req == 'time':
        return {'time':datetime.datetime.now().isoformat()}

    elif req == 'timestamp':
        return {'timestamp': datetime.datetime.now().timestamp() }

    elif req == 'log':
        with os.popen("journalctl -u ethoscope_node -rb") as log:
            l = log.read()
        return {'log': l}

    elif req == 'daemons':
        #returns active or inactive
        for daemon_name in SYSTEM_DAEMONS.keys():

            with os.popen("systemctl is-active %s" % daemon_name) as df:
                SYSTEM_DAEMONS[daemon_name]['active'] = df.read().strip()
        return SYSTEM_DAEMONS

    elif req == 'folders':
        return CFG.content['folders']

    elif req == 'users':
        return CFG.content['users']

    else:
        raise NotImplementedError()


@app.get('/client-actions/<action>')
def client_actions(action):

    if action == "restart":
        logger.info('User requested a service restart.')
        subprocess.Popen("sleep 1 && systemctl restart IDOC.service", shell=True)
        return ""

def stop(signo=None, _frame=None):
    logger.info("Received signal %s", signo)
    sys.exit(0)

signals = ('TERM', 'HUP', 'INT')
for sig in signals:
    signal.signal(getattr(signal, 'SIG' + sig), stop)


SERVER = get_server(PORT)
bottle.run(app, host='0.0.0.0', port=PORT, debug=DEBUG, server=SERVER)
