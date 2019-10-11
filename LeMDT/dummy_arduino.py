import logging

class Pin():

    def __init__(self, pin_number):

        self.pin_number = pin_number
        self.log = logging.getLogger(__name__)

    
    def write(self, value):
        self.log.info('Pin number {} ---> {}'.format(self.pin_number, value))



class Dummy():

    def __init__(self, port):
        
        self.port = port
        self.digital = [Pin(pin_number) for pin_number in range(70)]
    

