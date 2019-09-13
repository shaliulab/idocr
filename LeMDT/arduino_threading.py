# Standard library imports
import datetime
import logging
import sys
import threading
import warnings

# Third party imports
import numpy as np

# Local application imports
from lmdt_utils import setup_logging, _toggle_pin

# Set up package configurations
setup_logging()

class ArduinoThread(threading.Thread):

    def __init__(self, device, kwargs, name = None, stop_event_name = 'exit'):

        self.device = device
        self.log = logging.getLogger(__name__)
        self.pin_name =  name.split('-')[1]
        self.stop_event_name = stop_event_name
        super(ArduinoThread, self).__init__(name = name, target = self.pin_thread, kwargs = kwargs)


    def start(self, start_time, duration):
        """
        Extend the start method in threading.Thread() to receive 2 more args, start_time and duration

        """
        self._kwargs["start_time"] = start_time
        self._kwargs["duration"] = duration 
        super(ArduinoThread, self).start()
    
    def wait(self, waiting_time):
        event = getattr(self.device.interface, self.stop_event_name)
        if not event.is_set():
            event.wait(waiting_time)
        
        if event.is_set():
            sys.exit(1)


        # if self.device.interface.pause:
            # self.log.info('Waiting for play button press')
            # self.device.interface.play_event.wait()


    def pin_thread(self, pin_number, duration, start_time, start, end, on, off, block, event_index, n_iters=np.nan, d_name=None, board=None):
        """
        Run a single Arduino event in a separate thread independently.
        
        Run by every thread independently, this function implements the event specified in the corresponding row
        of the paradigm dataframe. Turns on a pin at a specific timepoint and after some waiting time, it turns it off
        If on and off are not none, it can implement a cycle during this waiting time i.e. the pin can be turned on and off
        between start and end for on and off seconds respectively.

        Parameters
        ----------
        pin_number: int
            Number of the pin on the Arduino board.
          
        duration: float
            time in seconds that the whole paradigm is supposed to last.
            After duration, all pins should go off, no matter what their program is.
          
        start_time: datetime.datetime
            Exact moment when run() (the function that calls pin_thread when defining the threads) is executed.
            Only makes sense in scheduled pins.
          
        start: float
            timepoint in seconds when the pin should go on for the first time.
            Only makes sense in scheduled pins.
            Not the same as start_time because the pin does not go ON from time 0,
            in most cases there is a waiting time.
          
        end: float
            timepoint in seconds when the pin should be turned off for good.
          
        on: float
            duration of the on time in a cycle.
            Only makes sense in intermitent pins.
          
        off: float
            duration of the off time in a cycle.
            Only makes sense in intermitent pins.
          
        n_iters: int, optional
            Number of cycles required by intermitent pins (as instructed in the program).
            Default is None
            If the pin does not have a cycle it will remain None.

        Returns
        -------
        int
            1 for normal runs and 0 for early exits.

        """
        sync_time = 1
        # d = threading.currentThread()


        # this is true for pins of type: CI, SI (intermitent)
        # i.e. threads where on is not NaN
        if n_iters != n_iters and on == on:
            n_iters = int(max(0, (min(end, duration) - start) / (on + off))) # check if total time is accessible
            # better using int( / ) than // or np.floor_divide becuase 1 // 0.2 = 4 and not 5 
        if n_iters > 0:
            self.log.info("{} will cycle {} times: start {} end {} tt {}".format(d_name, n_iters, start, end, duration))
            
        baseline = self.device.interface.record_start if self.device.interface.record_start else self.device.interface.interface_start

        # halt all threads until start_time + sync_time is reached
        # wait until all threads are ready to begin
        sleep1 = (baseline + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        stop = self.wait(sleep1)
        self.log.info('{} running'.format(d_name))
        if stop:
            self.toggle_pin(pin_number=pin_number, value=0)
            return 0
    
        thread_start = datetime.datetime.now()    
        
        # halt the thread until start_time + time sleep in the syncing + start is reached
        # i.e. wait until it is time to turn on a pin
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            stop = self.wait(sleep2)
            if stop:
                self.log.debug("{} received exit".format(d_name))
                self.toggle_pin(pin_number=pin_number, value=0)
                return 0
        else:
             self.log.warning("{} delayed {} seconds".format(d_name, -sleep2))
    
        
        # pin_id = self.mapping.query('pin_number == "{}"'.format(pin_number)).index[0]

        ##############
        # It's time to activate the Arduino
        self.device.paradigm.iloc[event_index,:]["active"] = True

        self.device.active_block[block] = True

        # false if n_iters is np.nan
        if n_iters == n_iters:    
            for _ in range(int(n_iters)):

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number=pin_number, value=1, freq=1/(on + off))
                
                runtime = datetime.datetime.now() - start_time
                sleep_time = on - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))

                else:
                    stop = self.wait(sleep_time)
                    if stop:
                        self.toggle_pin(pin_number=pin_number, value=0)
                        return 0

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number=pin_number, value=0, freq=1/(on + off))
                runtime = datetime.datetime.now() - start_time
                sleep_time = off - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    stop = self.wait(sleep_time)
                if stop:
                    self.toggle_pin(pin_number=pin_number, value=0, freq=0)
                    return 0

        else:
            # pins without cycle
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number=pin_number, value=1)
            sleep_time = min(end - start, duration - start)
            if sleep2 < 0:
                sleep_time += sleep2

            #time.sleep(sleep_time)
            stop = self.wait(sleep_time)
            if stop:
                self.toggle_pin(pin_number=pin_number, value=0)
                return 0

        self.device.pin_state[self.pin_name] = False
        self.toggle_pin(pin_number=pin_number, value=0)
        self.log.info("{} stopped".format(d_name))

        # Check if there's any thread from the current block that's still active
        self.device.active_block[block] = np.any(self.device.paradigm.query('block == "{}"'.format(block))["active"])
        # communicate to interface that current thread is finished
        self.device.threads_finished[d_name] = True
        # check if it was the last (in that case, the reduce method returns True)
        arduino_done = np.bitwise_and.reduce(list(self.device.threads_finished.values()))
        # if its the last, signal exit
        if arduino_done:
            self.device.close()

        return 1

ArduinoThread.toggle_pin = _toggle_pin

