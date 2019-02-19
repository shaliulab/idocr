import cv2
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# load video
cap = cv2.VideoCapture('outpy05.avi')
VIDEO_WIDTH = cap.get(3)
VIDEO_HEIGHT = cap.get(4)
print("The video has a resolution of width ({0}) by height({1})".format(VIDEO_WIDTH, VIDEO_HEIGHT))
ret, frame = cap.read()
if ret == True:
    print("Successful reading of video")
else:
    print("Video is not read correctly!")

cv2.namedWindow('ORIGIN')
cv2.moveWindow('ORIGIN', 1, 1)
cv2.resizeWindow('ORIGIN', 640, 512)
cv2.imshow('ORIGIN', frame)
cv2.waitKey(0)
cap.release()
cv2.destroyAllWindows()



