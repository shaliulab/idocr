import cv2
import numpy as np
import matplotlib.pyplot as plt
import time

# Set up general settings
# VideoPath = '8.avi'

VideoPath = 0

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
id_arena = 0
id_object = 0
accuImage = np.zeros((gray.shape[0], gray.shape[1],N), np.uint8)
min_arena_area = 1000
max_object_area = 200
min_obj_arena_dist = 10
duration = 300
while True:
    # Read one frame
    frameNo = int(cap.get(1))
    time_position = int(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
    ret, img = cap.read()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    first_frames.append(gray)
    cv2.putText(img,'Frame: '+str(cap.get(1)), (25,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)

    if frameNo < N:
        accuImage[:,:,frameNo] = gray
        avgImage = np.average(accuImage, 2).astype('uint8')

        image_blur = cv2.GaussianBlur(avgImage, (kernel_factor, kernel_factor), 0)
        _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
        image1_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, kernel)
        (_,contours0,_) = cv2.findContours(image1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


    if ret == True:

        img3 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)

        (im1, contours1, hierarchy1) = cv2.findContours(img3, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours0:
            if cv2.contourArea(c) < min_arena_area:
                continue
            id_arena +=1
            cnt = c
            area_contour = cv2.contourArea(c)
            (X,Y,W,H) = cv2.boundingRect(c)
            M0 = cv2.moments(cnt)
            if M0['m00'] != 0 and M0['m10']:
                CX1 = int(M0['m10']/M0['m00'])
                CY1 = int(M0['m01']/M0['m00'])

            print('Contour {} has an area of {}'.format(id_arena, area_contour))
            cv2.putText(img, 'Arena '+str(id_arena), (X-50,Y-50),cv2.FONT_HERSHEY_SIMPLEX, 1, (170,40,0), 2)
            cv2.drawContours(img, [c], 0, (255,255,0), 1)
            cv2.rectangle(img, (X,Y), (X+W,Y+H), (0,255,255), 2)
            cv2.circle(img, (CX1, CY1), 2, (255,0,0), -1)

            for c1 in contours1:
                if cv2.contourArea(c1)>max_object_area:
                    # print('Contour not found')
                    continue
                print('Find contour')
                id_object += 1
                cnt1 = c1
                (x, y, w, h) = cv2.boundingRect(c1)
                M1 = cv2.moments(cnt1)
                if M1['m00'] != 0 and M1['m10']:
                    cx1 = int(M1['m10']/M1['m00'])
                    cy1 = int(M1['m01']/M1['m00'])
                if cv2.pointPolygonTest(c, (cx1,cy1), True) < min_obj_arena_dist:
                    continue
                cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
                cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
        
        cv2.imshow('image', img)
        time.sleep(0.2)

        if cv2.waitKey(1) & 0xFF in [27, ord('q')] or ret == False or  time_position > duration:
            break
cap.release()
cv2.destroyAllWindows
