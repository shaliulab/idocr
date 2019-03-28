FROM python:3
RUN mkdir src src/Camera mkdir src/Arduino src/Arduino/mappings src/Arduino/programs
COPY src/Camera/track_OOP.py src/Camera/track_OOP.py
COPY src/Arduino/learning_memory.py src/Arduino/learning_memory.py
COPY main.py main.py
COPY src/Arduino/mappings/main.csv src/Arduino/mappings/main.csv
COPY src/Arduino/programs/main.csv src/Arduino/programs/main.csv
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install opencv-contrib-python
RUN pip install pyfirmata
RUN wget https://github.com/basler/pypylon/releases/download/1.3.1/pypylon-1.3.1-cp36-cp36m-linux_x86_64.whl
RUN pip install pypylon-1.3.1-cp36-cp36m-linux_x86_64.whl
CMD ["python", "main.py·", "--track", "--camera", "pylon", "--arduino", "--mappings", "Arduino/mappings/main.csv", "--sequence", "Arduino/programs/main.csv", "--fps", "2"]

