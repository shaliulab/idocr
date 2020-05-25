from pyfirmata import ArduinoMega as Arduino
import time

port = '/dev/ttyACM0'

board = Arduino(port)
pin_03 = board.get_pin('d:3:p')
pin_04 = board.get_pin('d:4:p')
list_of_pins = [pin_03, pin_04]

while True:
    [p.write(1) for p in list_of_pins]
    time.sleep(1/50)
    [p.write(0) for p in list_of_pins]
    time.sleep(.1)



