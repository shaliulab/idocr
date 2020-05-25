#! /bin/bash
cd /home/vibflysleep/VIBFlySleep/LeMDT
rm wheels/LeMDT*
python3 setup.py sdist bdist_wheel
ln dist/LeMDT-0.0.1-py3-none-any.whl wheels/
