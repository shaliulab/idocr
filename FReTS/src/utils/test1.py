import cv2
import matplotlib.pyplot as plt
import numpy as np

img = cv2.imread('test04.jpg')
# cap = cv2.VideoCapture('8.avi')
# cap.set(1, 68)
# ret, img = cap.read()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

kernel_factor = 5
LOW_1 = 50
UPPER_1 = 90
LOW_2 = 0
UPPER_2 = 255


kernel = np.ones((kernel_factor,kernel_factor), np.uint8)
erosion = cv2.erode(img, kernel, iterations=1)
dilation = cv2.dilate(img, kernel, iterations=1)
closing = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
opening = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

blur1 = cv2.medianBlur(gray, kernel_factor)
blur2 = cv2.GaussianBlur(gray, (kernel_factor,kernel_factor),0)

img_range = cv2.inRange(gray, LOW_1, UPPER_1)

ret1, img1 = cv2.threshold(blur2, LOW_2, UPPER_2, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
img2 = cv2.adaptiveThreshold(gray, UPPER_2, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10)

img3 = cv2.adaptiveThreshold(img_range, UPPER_2, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)

img3_opening = cv2.morphologyEx(img3, cv2.MORPH_OPEN, kernel)

img1_opening = cv2.morphologyEx(img1, cv2.MORPH_OPEN, kernel)

(im, contours, hierarchy) = cv2.findContours(img1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
(im1, contours1, hierarchy1) = cv2.findContours(img3_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


i = 0 
for c in contours:
    if cv2.contourArea(c) <150:
        continue
    i+=1
    area_contour = cv2.contourArea(c)
    print('Contour {} has an area of {}'.format(i, area_contour))
    cv2.drawContours(img, [c], 0, (255,255,0), 2)

    for c1 in contours1:
        if cv2.contourArea(c1)>200:
            # print('Contour not found')
            continue
        print('Find contour')
        cnt1 = c1
        (x, y, w, h) = cv2.boundingRect(c1)
        M = cv2.moments(cnt1)
        if M['m00'] != 0 and M['m10']:
            cx1 = int(M['m10']/M['m00'])
            cy1 = int(M['m01']/M['m00'])
        if cv2.pointPolygonTest(c, (cx1,cy1), True) < 10:
            continue
        cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
        cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
        # cv2.circle(img, (cx1,cy1), 2, (0,0,255), -1)
    

# titles = ['Original', 'Gray', 'Erosion', 'Dilation', 'Closing', 'Opening']
# images = [img, gray, erosion, dilation, closing, opening]
titles = ['Original', 'Gray', 'inRange', 'OTSU threshold', 'GaussianC', 'MeanC']
images = [img, gray, img_range, img1, img2, img3]

for i in range(6):
    plt.subplot(2,3,i+1), plt.imshow(images[i], 'gray')
    plt.title(titles[i])
    plt.xticks([]), plt.yticks([])



plt.show()

cap = cv2.VideoCapture(0)
import datetime
now = datetime.datetime.now()
while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret1, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
    # im2, contours2, hierarchy2 = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # cap_pos_time = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap_pos_time = str(datetime.datetime.now()-now)+' seconds'
    cap_pos_frame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cam_fps = int(cap.get(cv2.CAP_PROP_FPS))
    cv2.putText(frame, str(cap_pos_time), (25,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)
    cv2.putText(frame, str(cap_pos_frame), (25,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255),2)
    cv2.putText(frame, str(cam_fps), (25,75), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,255),2)
    # for i in contours2 :
    #     if cv2.contourArea(i)>1000:
    #         cnt2 = i
    #         hull = cv2.convexHull(cnt2)
    #         cv2.drawContours(frame, [hull], -1, (255,0,0), 1)
    cv2.imshow('test', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()


if cv2.waitKey(1) & 0xFF in [27, ord('q')]:
    cv2.destroyAllWindows()
