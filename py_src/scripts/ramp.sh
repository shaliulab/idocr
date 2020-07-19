#! /bin/bash

for i in $(seq 0 1 .1)
do
    python control.py --pins 5 --value $i --duration 60 --port /dev/ttyACM0
    python control.py --pins 6 --value $i --duration 60 --port /dev/ttyACM0
done
