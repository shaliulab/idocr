# Standard library imports
import logging

# Local application imports
from .lmdt_utils import setup_logging, _toggle_pin

setup_logging()
log = logging.getLogger(__name__)

class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.result = None
        self.log = log

    def create(self):
        """
        """
        
        pass
 
    def run(self):
        '''
        '''
        while not self.interface.exit.is_set() and self.result != 0:
            self.result = input('Proceed?: ')
            if not self.result in ['n', 'no','N', 'no']:
                self.result = self.proceed()
            else:
                self.log.info('Not proceeding')
        
        self.close()
 

    def apply_updates(self):
        pass         

    def close(self):
        """
        Quit the GUI and run the interface.close() method
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """
        self.interface.answer = input('Save results? Y/n')
        if not self.interface.answer is None:
            self.interface.close()
    
    def proceed(self):
        if not self.interface.play_event.is_set():
            self.interface.play()
            self.log.info('Play pressed')
            return 1
        elif not self.interface.arena_ok_event.is_set():
            self.interface.ok_arena()
            self.log.info('Arena ok pressed')
            return 1

        elif not self.interface.record_event.is_set():
            self.log.info('Record pressed')
            self.interface.record()
            return 1
        else:
            return 0
    

CLIGui.toggle_pin = _toggle_pin