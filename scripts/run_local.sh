#! /bin/bash
cd /home/vibflysleep/VIBFlySleep/LeMDT
#bash -c 'LD_LIBRARY_PATH=/home/vibflysleep/anaconda3/envs/py37/bin/../lib/ /home/vibflysleep/anaconda3/envs/py37/bin/python -m LeMDT --track --camera pylon --arduino --gui_name tkinter'
#bash -c 'LD_LIBRARY_PATH=/home/vibflysleep/anaconda3/envs/py37/bin/../lib/ /home/vibflysleep/anaconda3/envs/py37/bin/python -q -X faulthandler -m LeMDT --track --camera pylon --arduino --gui cli'
python -q -X faulthandler -m LeMDT 

