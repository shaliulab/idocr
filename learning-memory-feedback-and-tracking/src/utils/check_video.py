import cv2
import argparse

ap = argparse.ArgumentParser()

ap.add_argument("-v", "--video", type=str)
args = ap.parse_args()
args = vars(args)

video = args["video"]
print(video)

cap = cv2.VideoCapture(video)

ret, frame = cap.read()
print(ret)
if frame is not None:
    print(frame.shape)
else:
    print(frame)
