from pyfirmata import ArduinoMega as Arduino
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port", type = str)
ap.add_argument("-v", "--value", type = int, help = "1/0")
ap.add_argument('--pins', nargs='+', help='List of pins', required=True)

args = ap.parse_args()
args = vars(args)

board = Arduino(args["port"])
#for p in args["pins"]:
[board.digital[int(p)].write(args["value"]) for p in args["pins"]]
