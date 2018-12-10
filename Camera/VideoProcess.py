import cv2
import numpy as np
import matplotlib.pyplot as plt
import time

# Set up general settings
VideoPath = '8.avi'

# VideoPath = 0

# Capture video/streams
cap = cv2.VideoCapture(VideoPath)
RangeLow = 50
RangeUp = 90    
RangeLow1 = 0
RangeUp1 = 255  
kernel_factor = 5
kernel = np.ones((kernel_factor,kernel_factor), np.uint8)
N =10
first_frames = []



while True:
    # Read one frame
    frameNo = int(cap.get(1))
    ret, img = cap.read()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    accuImage = np.zeros((gray.shape[0], gray.shape[1],N), np.uint8)

    if frameNo < N:
        # first_frames.append(img)

        # if frameNo == 0:
        #     accuImage = gray
        # else:
        #     accuImage = np.add(gray, accuImage)
        # print('Resolution: %d %d' %(accuImage.shape[0], accuImage.shape[1]))
        # avgImage = accuImage/(frameNo+1)
        accuImage[:,:,frameNo] = gray
        avgImage = np.average(accuImage, 2).astype('uint8')


        image_blur = cv2.GaussianBlur(avgImage, (kernel_factor, kernel_factor), 0)
        print('Resolution: %d %d' %(image_blur.shape[0], image_blur.shape[1]))
        _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
        print('Resolution: %d %d' %(image1.shape[0], image1.shape[1]))
        image1_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, kernel)
        (_,contours0,_) = cv2.findContours(image1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


    # Change to gray scale


    if ret == True:
        # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  
        # _, thresh1 = cv2.threshold(gray, RangeLow, RangeUp, cv2.THRESH_BINARY)
        
        # gray1 = cv2.bitwise_and(gray, gray, mask = thresh1)
        # Blur gray image based on (5,5) kernel
        # blur0 = cv2.medianBlur(gray, 5)
        # blur = cv2.GaussianBlur(gray, (kernel_factor, kernel_factor), 0)
        
        # ret1, img1 = cv2.threshold(blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        # img1_opening = cv2.morphologyEx(img1, cv2.MORPH_OPEN, kernel)
        # Set up threshold limits
        img3 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)

        # (im, contours, hierarchy) = cv2.findContours(img1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnt = contours0[0]
        cv2.drawContours(img, contours0, -1, (255,255,0), 2)

        (im1, contours1, hierarchy1) = cv2.findContours(img3, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        cv2.putText(img,'Frame: '+str(cap.get(1)), (25,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        
        for c1 in contours1:
            if cv2.contourArea(c1) < 20 or cv2.contourArea(c1)>200:
                continue
            cnt1 = c1
            (x, y, w, h) = cv2.boundingRect(c1)
            M = cv2.moments(cnt1)
            if M['m00'] != 0 and M['m10']:
                cx1 = int(M['m10']/M['m00'])
                cy1 = int(M['m01']/M['m00'])
            if cv2.pointPolygonTest(cnt, (cx1,cy1), True) < 5:
                continue
            
            
            cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
            cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
            cv2.circle(img, (cx1,cy1), 2, (0,0,255), -1)
        
        cv2.imshow('image', img)
        time.sleep(0.2)

        if cv2.waitKey(1) & 0xFF in [27, ord('q')] or ret == False:
            break
cap.release()
cv2.destroyAllWindows
