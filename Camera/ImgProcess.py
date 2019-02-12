import cv2
import numpy as np
import matplotlib.pyplot as plt
import scipy

# Set up general settings
# VideoPath = '8.avi'

# # VideoPath = 0

# #k = cv2.waitKey(0) & 0xFF

# # Capture video/streams
# cap = cv2.VideoCapture(VideoPath)
# frameNo = 1
# cap.set(cv2.CAP_PROP_POS_FRAMES, frameNo)
# # cap.set(1, frameNo)
# # Read one frame
# ret, img = cap.read()
# Change to gray scale
cap = cv2.VideoCapture('outpy04.avi')
_, img = cap.read()

img = cv2.imread('test01.jpg')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Blur gray image based on (5,5) kernel
blur0 = cv2.medianBlur(gray, 5)
blur = cv2.GaussianBlur(gray, (5,5), 0)
# Set up threshold limits
RangeLow = 50
RangeUp = 70
RangedImg = cv2.inRange(gray, RangeLow, RangeUp)
#Different threshold methods
# Basic BINARY thresholding
ret1, thresh1 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_BINARY)
# Inverted BINARY thresholding
ret2, thresh2 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_BINARY_INV)
# Trunck thresholding
ret3, thresh3 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_TRUNC)
# ToZero/ToZeroInverted thresholding
ret4, thresh4 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_TOZERO)
ret5, thresh5 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_TOZERO_INV)
# Adaptive thresholding MEAN_C

thresh6 = cv2.adaptiveThreshold(gray, RangeUp, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)

thresh7 = cv2.adaptiveThreshold(gray, RangeUp, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 13, 10)
# OTSU thresholding
ret8, thresh8 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
ret9, thresh9 = cv2.threshold(blur, 10, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

titles = ['Original', 'Gray', 'Blur', 'Binary', 'BinaryInv', 'Trunc', 'ToZero', 'ToZeroInv', 'AdaptiveMeanC', 'AdaptiveGaussianC', 'GrayOTSU', 'BlurOTSU']
# images = [img, gray, blur, thresh1, thresh2, thresh3, thresh4, thresh5, thresh6, thresh7, thresh8, thresh9]

# for i in range(12):

#     plt.subplot(4, 3, i+1), plt.imshow(images[i], 'gray')
#     plt.title(titles[i])
#     plt.xticks([]), plt.yticks([])
# plt.imshow(thresh9, 'gray')
# plt.xticks([]), plt.yticks([])
gray1 = cv2.bitwise_and(gray, gray, mask=thresh1)
gray2 = cv2.inRange(gray1, RangeLow, RangeUp)
RangedImg1 = cv2.cvtColor(RangedImg, cv2.COLOR_GRAY2BGR)
fgbg = cv2.createBackgroundSubtractorMOG2()
fgmask = fgbg.apply(gray2)
fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))


detector = cv2.SimpleBlobDetector()
keypoints = detector.detect(gray2)
img_with_keypoints = cv2.drawKeypoints(img, keypoints, None, (255,0,0), flags = cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)


(im, contours, hierarchy) = cv2.findContours(thresh1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
for c in contours:
    if cv2.contourArea(c) < 300:
        continue    
    cnt0 = c
    epsilon0 = 0.5*cv2.arcLength(cnt0, True)
    approx0 = cv2.approxPolyDP(cnt0, epsilon0, True)
    cv2.drawContours(RangedImg1, [c], -1, (255,0,0),1)
    cv2.drawContours(img, [c], -1, (255,0,0), 1)
    cv2.drawContours(gray2, [c], -1, (255,0,0), -1)
# gray3 = gray1
# gray3[contours[0][:,0], contours[0][:,1]] = 1 

(im1, contours1, hierarchy1) = cv2.findContours(RangedImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
for c1 in contours1:
    if cv2.contourArea(c1) > 300 or cv2.contourArea(c1) < 20:
        continue
    cnt = c1
    epsilon = 0.005*cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    cv2.drawContours(img, [approx], -1, (0,0,255), 1)
    cv2.drawContours(RangedImg1, [approx], -1, (0,0,255), 1)



plt.subplot(2, 2, 1), plt.imshow(img, 'gray')
plt.title('Original')
plt.xticks([]), plt.yticks([])
plt.subplot(2, 2, 2), plt.imshow(fgmask, 'gray')
plt.title('Gray')
plt.xticks([]), plt.yticks([])
plt.subplot(2 , 2, 3), plt.imshow(thresh1, 'gray')
plt.title('BINARY')
plt.xticks([]), plt.yticks([])
plt.subplot(2, 2, 4), plt.imshow(RangedImg1, 'gray')
plt.title('RangedImg')
plt.xticks([]), plt.yticks([])

plt.show()

# drawing = False # true if mouse is pressed
# mode = True # if True, draw rectangle. Press 'm' to toggle to curve
# ix,iy = -1,-1
# gray1 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
# img = gray1
# mouse callback function
# def draw_circle(event,x,y,flags,param):
#     global ix,iy,drawing,mode
    

#     if event == cv2.EVENT_LBUTTONDOWN:
#         drawing = True
#         ix,iy = x,y

#     elif event == cv2.EVENT_MOUSEMOVE:
#         if drawing == True:
#             if mode == True:
                
#                 cv2.rectangle(img,(ix,iy),(x,y),(0,255,0),2)
                
#             else:
#                 cv2.circle(img,(ix,iy),int(np.sqrt((ix-x)**2+(iy-y)**2)),(0,0,255),2)

#     elif event == cv2.EVENT_LBUTTONUP:
#         drawing = False
#         if mode == True:
#             cv2.rectangle(img,(ix,iy),(x,y),(0,255,0),2)
#         else:
#             cv2.circle(img,(ix,iy),int(np.sqrt((ix-x)**2+(iy-y)**2)),(0,0,255),2)

# cv2.namedWindow('image')

# cv2.setMouseCallback('image',draw_circle)

# while(1):
#     cv2.imshow('image', imgShow)
#     k = cv2.waitKey(1) & 0xFF
#     if k == ord('m'):
#         mode = not mode
#     elif k in [27, ord('q')]:
#         break

if cv2.waitKey(1) & 0xFF in [27, ord('q')]:
    cv2.destroyAllWindows()

