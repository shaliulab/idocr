import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

img = cv2.imread('test01.jpg', 0)
blur = cv2.GaussianBlur(img, (5,5),0)

ret1,thresh1 = cv2.threshold(img,127,255,cv2.THRESH_BINARY)
ret2,thresh2 = cv2.threshold(img,127,255,cv2.THRESH_BINARY_INV)
ret3,thresh3 = cv2.threshold(img,127,255,cv2.THRESH_TRUNC)
ret4,thresh4 = cv2.threshold(img,127,255,cv2.THRESH_TOZERO)
ret5,thresh5 = cv2.threshold(img,127,255,cv2.THRESH_TOZERO_INV)

thresh6 = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,11,2)
thresh7 = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,11,2)

ret8,thresh8 = cv.threshold(img,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)
ret9,thresh9 = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)

for i in xrange()