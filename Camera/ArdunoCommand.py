import serial
from serial.tools import list_ports

_baud = 115200

ports = list_ports.comports()
all_ports = set()

for i in len(ports):
    port_device, port_name, _ = ports[i]
    if 'USB' in port_name:
        _serial = serial.Serial(port_device, _baud, timeout = 0)
        if _serial.is_open:
            all_ports |= {port_device}
            
            
from pyfirmata import Arduino, util
import time

board = Arduino("COM6")
loopTimes = input('How many times would you like the LED to blink: ')
print("Blinking " + loopTimes + " times.")

for x in range(int(loopTimes)):
    board.digital[12].write(1)
    time.sleep(0.1)
    board.digital[12].write(0)
    time.sleep(0.1)






import serial #Serial imported for Serial communication
import time #Required to use delay functions
 
ArduinoSerial = serial.Serial('COM6',115200) #Create Serial port object called arduinoSerialData
time.sleep(2) #wait for 2 secounds for the communication to get established

print (ArduinoSerial.readline()) #read the serial data and print it as line
print ("Enter 1 to turn ON LED and 0 to turn OFF LED")

 
while 1: #Do this forever

    var = input() #get input from user
    print ("you entered", var) #print the intput for confirmation
    
    if (var == '1'): #if the value is 1
        ArduinoSerial.write('1') #send 1
        print ("LED turned ON")
        time.sleep(0.1)
    
    if (var == '0'): #if the value is 0
        ArduinoSerial.write('0') #send 0
        print ("LED turned OFF")
        time.sleep(0.1)


