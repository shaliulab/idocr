# Standard library imports
import datetime
import logging
import threading
import warnings

# Third party imports
import numpy as np

# Local application imports
from src.utils.frets_utils import setup_logging

# Set up package configurations
setup_logging()

class ArduinoThread(threading.Thread):

    def __init__(self, lmd, kwargs, name = None):

        self.lmd = lmd
        self.log = logging.getLogger(__name__)
        super(ArduinoThread, self).__init__(name = name, target = self.pin_thread, kwargs = kwargs)


    def start(self, start_time, duration):
        """
        Extend the start method in threading.Thread() to receive 2 more args, start_time and duration

        """
        self._kwargs["start_time"] = start_time
        self._kwargs["duration"] = duration 
        super(ArduinoThread, self).start()


    def pin_thread(self, pin_number, duration, start_time, start, end, on, off, n_iters=np.nan, d_name=None, board=None):
        """
        Run by every thread independently, this function replicates the program specified in the corresponding row
        of the program dataframe. Turns on a pin at a specific timepoint and after some waiting time, it turns it off
        If on and off are not none, it can implement a cycle during this waiting time i.e. the pin can be turned on and off
        between start and end for on and off seconds respectively.

        Keywords
          pin_number: integer declaring the number of the pin on the Arduino board
          
          duration: time in seconds that the whole program is supposed to last.
                       After duration, all pins should go off, no matter what their program is
          
          start_time: datetime object declaring the exact moment when run()
          (the function that calls pin_thread when defining the threads) is executed. Only makes sense in scheduled pins.
          
          start: timepoint in seconds when the pin should go on for the first time. Only makes sense in scheduled pins.
          
          end: timepoint in seconds when the pin should be turned off for good
          
          on: duration of the on time in a cycle. Only makes sense in intermitent pins.
          
          off: duration of the off time in a cycle. Only makes sense in intermitent pins.
          
          n_iters: By default is None, but it will be asigned a value equal to the number of cycles
                   required by intermitent pins (as instructed in the program). If the pin does not have a cycle,
                   then it will still be None        
        """
        sync_time = 1
        # d = threading.currentThread()


        # this is true for pins of type: CI, SI (intermitent)
        # i.e. threads where on is not NaN
        if n_iters != n_iters and on == on:
            n_iters = max(0, (min(end, duration) - start) // (on + off)) # check if total time is accessible
        if n_iters > 0:
            self.log.info("{} will cycle {} times: start {} end {} tt {}".format(d_name, n_iters, start, end, duration))
            
        
        # halt all threads until start_time + sync_time is reached
        # wait until all threads are ready to begin
        sleep1 = (self.lmd.interface.init_time + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        stop = self.lmd.interface.exit.wait(sleep1)
        self.log.info('{} running'.format(d_name))
        if stop:
            self.toggle_pin(pin_number, 0)
            return 0
    
        thread_start = datetime.datetime.now()    
        
        # halt the thread until start_time + time sleep in the syncing + start is reached
        # i.e. wait until it is time to turn on a pin
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            stop = self.lmd.interface.exit.wait(sleep2)
            if stop:
                self.log.debug("{} received exit".format(d_name))
                self.toggle_pin(pin_number, 0)
                return 0
        else:
             self.log.warning("{} delayed {} seconds".format(d_name, -sleep2))
    
        
        # pin_id = self.mapping.query('pin_number == "{}"'.format(pin_number)).index[0]
    
        if n_iters == n_iters:    
            for _ in range(int(n_iters)):

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 1)
                
                runtime = datetime.datetime.now() - start_time
                sleep_time = on - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))

                else:
                    stop = self.lmd.interface.exit.wait(sleep_time)
                    if stop:
                        self.toggle_pin(pin_number, 0)
                        return 0

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 0)
                runtime = datetime.datetime.now() - start_time
                sleep_time = off - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    stop = self.lmd.interface.exit.wait(sleep_time)
                if stop:
                    self.toggle_pin(pin_number, 0)
                    return 0
       

        else:
            # pins without cycle
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number, 1)
            sleep_time = min(end - start, duration - start)
            if sleep2 < 0:
                sleep_time += sleep2
   
            #time.sleep(sleep_time)
            stop = self.lmd.interface.exit.wait(sleep_time)
            if stop:
                self.toggle_pin(pin_number, 0)
                return 0

        self.toggle_pin(pin_number, 0)
        self.log.info("{} stopped".format(d_name))


        # communicate to interface that current thread is finished
        self.lmd.interface.threads_finished[d_name] = True
        # check if it was the last (in that case, the reduce method returns True)
        arduino_done = np.bitwise_and.reduce(list(self.lmd.interface.threads_finished.values()))
        # if its the last, signal exit
        if arduino_done:
            self.lmd.interface.exit.set()
            self.lmd.interface.arduino_done = arduino_done

        return 1
    
    def toggle_pin(self, pin_number, value):
        """
        Updates the state of pin pin_number with value, while logging and caching this
        so user can confirm it. TODO. Finish show_circuit and use message
        """

        d = threading.currentThread()
        
        # Update state of pin (value = 1 or value = 0)
        self.lmd.board.digital[pin_number].write(value)

        # Update log with info severity level unless
        # on pin13, then use severity debug
        f = self.log.info
        # if pin_number == 13: f = self.log.debug
        f("{} - {}".format(
            d._kwargs["d_name"],
            value
        ))

        # Create a new row in the metadata
        self.lmd.saver.process_row(
                d = {
                    "pin_number": pin_number, "value": value, "thread": d._kwargs["d_name"], 
                    "timestamp": self.lmd.interface.timestamp,
                    "datetime": datetime.datetime.now()
                    },
                key = "df"

        )
  
        #self.show_circuit(
        #            #pin_state,
        #            message
        #            )


    # def show_circuit(self, 
    #                 #pin_state,
    #                 message=None, flush=True):
    #    #global pin_state
    #    pin_state_g = {p: "x" if v == 1 else "0" for p, v in self.pin_state.items()}

    #    main_pins = self.lmd.mapping.query('pin_group == "main"').index.values[1:]
    #    left_pins = self.lmd.mapping.query('pin_group == "left"').index.values
    #    right_pins = self.lmd.mapping.query('pin_group == "right"').index.values
       
    #    show_data = [self.pin_id2n(p) for p in main_pins] + [pin_state_g[p] for p in main_pins]
    #    show_data2 = [self.left_pair(p, pin_state_g) for p in left_pins] 
    #    show_data3 = [self.left_pair(p, pin_state_g)[::-1] for p in right_pins] 
    #    show_data4 = list(zip(show_data2, show_data3))
    #    flatten = lambda l: [item for sublist in l for item in sublist]
    #    show_data4 = flatten(flatten(show_data4))
    #    show_data += show_data4
    #    n=4
    #    n2=18
    #    circuit = " " * 8 + "{}-VA  {}-MA  {}-IR  {}-VI   \n" +    " " * 8 + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]\n" +    "{}-LO1  [{}]" + " " * n2 + "[{}] RO1-{}\n" +    "{}-LO2  [{}]" + " " * n2 + "[{}] RO2-{}\n" +    "{}-LES  [{}]" + " " * n2 + "[{}] RES-{}\n" +    "{}-LL   [{}]" + " " * n2 + "[{}]  RL-{}\n"
    #    filled_circuit = circuit.format(*show_data)        
           
           
    #    if not message is None:
    #        output = "{}: {}\n{}".format(datetime.datetime.now(), message, filled_circuit)
    #    else:
    #        output = "{}: \n{}".format(datetime.datetime.now(), filled_circuit)
    #    if flush:
    #        nlines = len(filled_circuit.split('\n'))
    #        output = nlines * "\033[F\033[K" + output

    #    handle = open("pin_state.txt", "a+")
    #    handle.write(output)
    #    handle.close()