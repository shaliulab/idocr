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
            
