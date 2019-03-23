#! /bin/bash
cd /home/luna.kuleuven.be/u0127714/VIBFlySleepLab/FReTS
bash src/open_camera.sh
python main.py --track --video videos/output.avi --duration 999  --arduino  --mappings mappings/main.csv --sequence programs/learn.csv --gui
