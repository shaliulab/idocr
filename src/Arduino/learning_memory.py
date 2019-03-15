from pyfirmata import ArduinoMega as Arduino # import the right board but always call it Arduino
from pyfirmata import Pin
from pyfirmata import util
import numpy as np
import warnings
from tqdm import tqdm
import pandas as pd
import sys
import threading
import logging
import datetime
# import ipdb
import time
#import pickle # share pin state across threads
import glob
import os # file removal and we cleaning
import argparse
import timeit
import signal
import serial


def convert(s):
    try:
        return np.float(s)
    except ValueError:
        num, denom = s.split('/')
        return np.float(num) / np.float(denom)

class MyThread(threading.Thread):
    def start(self, program_start, total_time):
        """
        Extend the start method in threading.Thread() to receive 2 more args, program_start and total_time

        """
        self._kwargs["program_start"] = program_start
        self._kwargs["total_time"] = total_time 
        super(MyThread, self).start()


class LearningMemoryDevice():
    def __init__(self, mapping, program, port, log_dir, communicate=True):

        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")
        program = pd.read_csv(program, skip_blank_lines=True, comment="#")
        mapping = mapping.set_index('pin_id')
        program = program.set_index('pin_id')
        program['start'] = program['start'].apply(convert)
        program['end'] = program['end'].apply(convert)
        program['on'] = program['on'].apply(convert)
        program['off'] = program['off'].apply(convert)
        print(program)
        program = program * 60


        self.mapping = mapping
        self.program = program 
        self.port = port
        pin_names = mapping.index
        pin_state = {p: 0 for p in pin_names}

        self.pin_state = pin_state

        try:
            self.board = Arduino(port)
        except serial.serialutil.SerialException:
            print('Please provide the correct port')
            sys.exit(1)
        #filehandler = open(os.path.join(log_dir, "pin_state.obj"),"wb")
        #pickle.dump(pin_state,filehandler)
        #filehandler.close()    
        self.exit = threading.Event()
        self.communicate = communicate
        self.quit = self.thread_off()

        self.log_dir = log_dir
        log_files = glob.glob(os.path.join(self.log_dir, 'log*'))
        for f in log_files + [os.path.join(self.log_dir, e) for e in "pin_state.txt"]:
            try:
                os.remove(f)
            except OSError:
                pass

    def check_do_run(self, d, max_sleep):
        stop = False 
        start_sleeping = datetime.datetime.now()
        while ((datetime.datetime.now() - start_sleeping).total_seconds() < max_sleep):
            if not self.exit.is_set():
                time.sleep(0.001)
    
                #print(getattr(d, "do_run"))
            else:
                stop = True
                break
        return stop 


    #def off(self):
    #    [self.board.digital[pin_number].write(0) for pin_number in self.mapping.pin_number]

    def prepare(self):
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        threads = {}
        
        count = {p: 0 for p in self.program.index}
        for p in self.program.index:
            d_pin_number = np.asscalar(self.mapping.loc[p]["pin_number"])
            x0 = count[p]
            x1 = count[p]+1

            d_start =      np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["start"])
            d_end =        np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["end"])
            d_on =         np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["on"])
            d_off =        np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["off"])
            d_name = 'thread-{}_{}'.format(p, count[p])

            kwargs = {
                "pin_number"   : d_pin_number,
                "start"        : d_start,
                "end"          : d_end,
                "on"           : d_on,
                "off"          : d_off,
                "total_time"   : None,
                "program_start": None,
                "d_name"         : d_name, 
                "board":         self.board

            }
            d = MyThread(name=d_name,
                         target=self.pin_thread,
                         kwargs = kwargs)

            d.setDaemon(False)
            d.do_run = True
            threads[d_name]=d
            count[p] += 1
        
        
        ## Signal start
#        for i in range(2):
#            for pin_number in self.mapping.pin_number:
#                self.board.digital[pin_number].write(1)
#                time.sleep(0.05)
#                self.toggle_pin(pin_number, 0)
#                time.sleep(0.05)
                
        self.program_start = datetime.datetime.now()

        # Make the main thread run quit when signaled to stop
        # This will stop all the threads in a controlled fashion,
        # which means all the pins are turned of before the thread
        # peacefully dies
        signals = ('TERM', 'HUP', 'INT')
        out_signals = [None,]*3
        for i, sig in enumerate(signals):
            #print(sig)
            out_sig = signal.signal(getattr(signal, 'SIG'+sig), self.quit)
            #print(out_sig)
            out_signals[i] = out_sig
            


        self.threads = threads
        return threads

    def toggle_pin(self, pin_number, value, message=None):

        d = threading.currentThread()
        # global self.pin_state

        print("{} setting pin {} to {} at {}".format(
            d._kwargs["d_name"],
            pin_number,
            value,
            datetime.datetime.now()))

        self.board.digital[pin_number].write(value)

        #if self.communicate:
            #filehandler = open(os.path.join(self.log_dir, "pin_state.obj"),"rb")
            #pin_state = pickle.load(filehandler)
            #filehandler.close()

            #pin_state[self.mapping.query('pin_number == "{}"'.format(pin_number))["pin_id"].iloc[0]]=value
            ##print(self.pin_state["RIGHT_ODOUR_2"])

            #filehandler = open(os.path.join(self.log_dir, "pin_state.obj"),"wb")
            #pickle.dump(pin_state,filehandler)
            #filehandler.close()
    
        self.show_circuit(
                    #pin_state,
                    message
                    )
 
 

    def pin_thread(self, pin_number, total_time, program_start, start, end, on, off, n_iters=np.nan, d_name="", board=None):
        """
        pin_number: integer declaring the number of the pin on the Arduino board
        
        total_time: time in seconds that the whole program is supposed to last.
                     After total_time, all pins should go off, no matter what their program is
        
        program_start: datetime object declaring the exact moment when run()
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
        #global self.pin_state
        d = threading.currentThread()


        # this is true for pins of type: CI, SI (intermitent)
        # i.e. threads where on is not NaN
        if n_iters != n_iters and on == on:
            #[print(type(e)) for e in [end, total_time, on, off]]
            n_iters = (min(end, total_time) - start) // (on + off) # check if total time is accessible
            print("{} will cycle {} times".format(d._kwargs["d_name"], n_iters))
            
        
        # halt all threads until program_start + sync_time is reached
        # wait until all threads are ready to begin
        sleep1 = (program_start + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        stop = self.check_do_run(d, sleep1)
        print('{} started running at {}'.format(d._kwargs["d_name"], datetime.datetime.now()))
        if stop:
            self.toggle_pin(pin_number, 0)
            return 0

    
        thread_start = datetime.datetime.now()    
        self.write_start_time(pin_number, "Pin {}-{} starts at {}\n", start)
        
        
        logging.debug("Running program on pin {}".format(pin_number))  
    
        # halt the thread until program_start + time sleep in the syncing + start is reached
        # i.e. wait until it is time to turn on a pin
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            stop = self.check_do_run(d, sleep2)
            if stop:
                #print("[INFO] Signaled exit")
                self.toggle_pin(pin_number, 0)
                return 0
        else:
            pass
    #         print(d_name.format(pin_number))
    #         print(sleep2)      
            
    #     self.write_start_time(pin_number, "Pin {}-{} executes at {}\n", start)
    
        
        pin_id = self.mapping.query('pin_number == "{}"'.format(pin_number)).index[0]
    
        if n_iters == n_iters:    
    #         for _ in tqdm(range(int(n_iters))):
            for _ in range(int(n_iters)):

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 1)
                
                runtime = datetime.datetime.now() - start_time
                sleep_time = on - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))

                else:
                    stop = self.check_do_run(d, sleep_time)
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
                    stop = self.check_do_run(d, sleep_time)
                if stop:
                    self.toggle_pin(pin_number, 0)
                    return 0
       

        else:
            # pins without cycle
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number, 1)
            sleep_time = min(end - start, total_time - start)
            if sleep2 < 0:
                sleep_time += sleep2
   
            #time.sleep(sleep_time)
            stop = self.check_do_run(d, sleep_time)
            if stop:
                self.toggle_pin(pin_number, 0)
                return 0
            #if stop:
            #    self.toggle_pin(pin_number, 0)
            #    return 0



            #time.sleep(sleep_time)
#            while ((datetime.datetime.now() - start_sleeping).total_seconds() < sleep_time):
#                if getattr(d, "do_run", True):
#                    pass
#                    #print(getattr(d, "do_run"))
#                else:
#                    break

        self.toggle_pin(pin_number, 0)



 
    def run(self, total_time, threads):
        [d.start(self.program_start, 60*total_time) for d in threads.values()]


 
    def show_circuit(self, 
                    #pin_state,
                    message=None, flush=True):
       #global pin_state
       pin_state_g = {p: "x" if v == 1 else "0" for p, v in self.pin_state.items()}
       #print(pin_state_g["RIGHT_ODOUR_2"])

       main_pins = self.mapping.query('pin_group == "main"').index.values[1:]
       left_pins = self.mapping.query('pin_group == "left"').index.values
       right_pins = self.mapping.query('pin_group == "right"').index.values
       
       show_data = [self.pin_id2n(p) for p in main_pins] + [pin_state_g[p] for p in main_pins]
       show_data2 = [self.left_pair(p, pin_state_g) for p in left_pins] 
       show_data3 = [self.left_pair(p, pin_state_g)[::-1] for p in right_pins] 
       show_data4 = list(zip(show_data2, show_data3))
       flatten = lambda l: [item for sublist in l for item in sublist]
       show_data4 = flatten(flatten(show_data4))
       show_data += show_data4
       n=4
       n2=18
       circuit = " " * 8 + "{}-VA  {}-MA  {}-IR  {}-VI   \n" +    " " * 8 + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]\n" +    "{}-LO1  [{}]" + " " * n2 + "[{}] RO1-{}\n" +    "{}-LO2  [{}]" + " " * n2 + "[{}] RO2-{}\n" +    "{}-LES  [{}]" + " " * n2 + "[{}] RES-{}\n" +    "{}-LL   [{}]" + " " * n2 + "[{}]  RL-{}\n"
       filled_circuit = circuit.format(*show_data)        
           
           
       if not message is None:
           output = "{}: {}\n{}".format(datetime.datetime.now(), message, filled_circuit)
       else:
           output = "{}: \n{}".format(datetime.datetime.now(), filled_circuit)
       if flush:
           nlines = len(filled_circuit.split('\n'))
           output = nlines * "\033[F\033[K" + output

       handle = open("pin_state.txt", "a+")
       handle.write(output)
       handle.close()


    def pin_id2n(self, pin_id):
        return str(self.mapping.loc[[pin_id]]["pin_number"].iloc[0]).zfill(2)
    
    def left_pair(self, p, pin_state_g):
        return [self.pin_id2n(p), pin_state_g[p]]


    def write_start_time(self, pin_number, message, start):
        
        handle = open(os.path.join(self.log_dir, "log_{}.txt".format(pin_number)), "a+")
        handle.write(message.format(pin_number, start, datetime.datetime.now()))
        handle.close()


    def total_off(self, exit=True):
        # stop all the threads
        if getattr(self, "threads", False):
            print("Quitting")
            for d in self.threads.values():
                #d.do_run = False
                try:
                    print("{} stopped running at {}".format(d._kwargs["d_name"], datetime.datetime.now()))
                except AttributeError:
                    pass
                #id.join()
        else:
            print("Setting all pins on Arduino to 0")
    
        for p in self.mapping.pin_number:
            self.board.digital[p].write(0)
    
        if exit:
            return False


    def thread_off(self):
        def quit(signo, _frame=None):
           print(signo)
           self.exit.set()
           self.total_off()
    
        return quit
    
if __name__ == "__main__":

    # Arguments to follow the command, adding video, etc options
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows", default = "/dev/ttyACM0")
    ap.add_argument("-m", "--mappings", type = str, help="Absolute path to csv providing pin number-pin name mappings", required=True)
    ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino", required=True)
    ap.add_argument("-l", "--log_dir",  type = str, help="Absolute path to directory where log files will be stored", default = "Arduino")
    ap.add_argument("-d", "--duration",  type = int, required=True)
    args = vars(ap.parse_args())


    mapping = args["mappings"]
    program = args["sequence"]

    device = LearningMemoryDevice(mapping, program, args["port"], args["log_dir"])
    device.total_off(exit=False)

    threads = device.prepare()
    total_time = 60*args["duration"]
    device.run(total_time=total_time, threads=threads)
    time.sleep(total_time)
    #device.exit.wait(args["duration"])
