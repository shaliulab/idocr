import argparse
import logging
import signal
import sys
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from pyfirmata import ArduinoMega as Arduino

ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port", type = str)
ap.add_argument("-v", "--value", type = float, help = "0-1")
ap.add_argument('--pins', nargs='+', help='List of pins', required=True)
ap.add_argument('--hertz', type=float)

args = ap.parse_args()
args = vars(args)

stop = False
def quit(signo=None, _frame=None):

    global stop
    logger.info("Received signal %s", signo)
    stop = True
    [board.digital[int(p)].write(0) for p in args["pins"]]

signals = ('TERM', 'HUP', 'INT')
for sig in signals:
    signal.signal(getattr(signal, 'SIG' + sig), quit)

board = Arduino(args["port"])
#for p in args["pins"]:

VALUE = args['value']
VALUE = 1 if VALUE == 1.0 else VALUE

PINS = {}
for p in args['pins']:
    if isinstance(VALUE, float):
        PINS[p] = board.get_pin('d:%d:p' % int(p))
    else:
        PINS[p] = board.get_pin('d:%d:o' % int(p))


if args['hertz'] is None:
    [PINS[p].write(args["value"]) for p in PINS]
    while not stop:
        time.sleep(1)

else:
    while not stop:
        [p.write(VALUE) for p in PINS.values()]
        time.sleep(1/(args['hertz']*2))
        [p.write(0) for p in PINS.values()]
        time.sleep(1/(args['hertz']*2))


