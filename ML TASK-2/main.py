import os

import cv2
import numpy as np
import matplotlib.pyplot as plt

import util

import easyocr

import imutils

# define constants
model_cfg_path = os.path.join('.', 'model', 'cfg', 'darknet-yolov3.cfg')
model_weights_path = os.path.join('.', 'model', 'weights', 'model.weights')
class_names_path = os.path.join('.', 'model', 'class.names')

#img_path = './Datacluster_number_plates (16).jpg'

input_dir = ''

for img_name in os.listdir(input_dir):
    img_path = os.path.join(input_dir, img_name)

    # load class names
    with open(class_names_path, 'r') as f:
        class_names = [j[:-1] for j in f.readlines() if len(j) > 2]
        f.close()

    # load model
    net = cv2.dnn.readNetFromDarknet(model_cfg_path, model_weights_path)

    # load image

    img = cv2.imread(img_path)

    H, W, _ = img.shape

    # convert image
    blob = cv2.dnn.blobFromImage(img, 1 / 255, (416, 416), (0, 0, 0), True)

    # get detections
    net.setInput(blob)

    detections = util.get_outputs(net)

    # bboxes, class_ids, confidences
    bboxes = []
    class_ids = []
    scores = []

    for detection in detections:
        # [x1, x2, x3, x4, x5, x6, ..., x85]
        bbox = detection[:4]

        xc, yc, w, h = bbox
        bbox = [int(xc * W), int(yc * H), int(w * W), int(h * H)]

        bbox_confidence = detection[4]

        class_id = np.argmax(detection[5:])
        score = np.amax(detection[5:])

        bboxes.append(bbox)
        class_ids.append(class_id)
        scores.append(score)

    # apply nms
    bboxes, class_ids, scores = util.NMS(bboxes, class_ids, scores)
    print(bboxes)
    # plot

    for bbox_, bbox in enumerate(bboxes):
        xc, yc, w, h = bbox
        print("hi",xc,yc,w,h)

        img = cv2.rectangle(img,
                            (int(xc - (w / 2)), int(yc - (h / 2))),
                            (int(xc + (w / 2)), int(yc + (h / 2))),
                            (0, 255, 0),
                            10)

        license_plate = img[int(yc - (h / 2)):int(yc + (h / 2)), int(xc - (w / 2)):int(xc + (w / 2)), :]

    license_plate_gray = cv2.cvtColor(license_plate, cv2.COLOR_BGR2GRAY)

    #_, license_plate_thresh = cv2.threshold(license_plate_gray, 64, 255, cv2.THRESH_BINARY)

    if len(bboxes)>0:
        reader = easyocr.Reader(['en'])
        output = reader.readtext(license_plate_gray)
        
        for out in output:
            _, text, text_score = out
            print(text)
        
        plt.figure()
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # plt.figure()
        # plt.imshow(cv2.cvtColor(license_plate, cv2.COLOR_BGR2RGB))
        
        plt.figure()
        plt.imshow(cv2.cvtColor(license_plate_gray, cv2.COLOR_BGR2RGB))

        # plt.show()

    else:
        #print("Its null")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) #convert image to gray
        bfilter = cv2.bilateralFilter(gray, 11, 17, 17) #Noise reduction
        #plt.imshow(cv2.cvtColor(bfilter, cv2.COLOR_BGR2RGB)) #show processed image
        #plt.title('Processed Image')

        edged = cv2.Canny(bfilter, 30, 200) #Edge detection
        #plt.imshow(cv2.cvtColor(edged, cv2.COLOR_BGR2RGB))

        keypoints = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) #Find contours 
        contours = imutils.grab_contours(keypoints) #Grab contours 
        contours = sorted(contours, key=cv2.contourArea, reverse=True) #Sort contours
        contours = contours[:10]

        #Loop over our contours to find the best possible approximate contour of 10 contours
        location = None
        #for contour in contours:
        approx = cv2.approxPolyDP(contours[0], 10, True)
        #if len(approx) == 4:
        location = approx
        #    break
            
        #print("Location: ", location)

        mask = np.zeros(gray.shape, np.uint8) #create blank image with same dimensions as the original image
        new_image = cv2.drawContours(mask, [location], 0,255, -1) #Draw contours on the mask image
        new_image = cv2.bitwise_and(img, img, mask=mask) #Take bitwise AND between the original image and mask image

        #plt.imshow(cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)) #show the final image

        (x,y) = np.where(mask==255) #Find the co-ordinates of the four corners of the document
        (x1, y1) = (np.min(x), np.min(y)) #Find the top left corner
        (x2, y2) = (np.max(x), np.max(y)) #Find the bottom right corner
        cropped_image = gray[x1:x2+1, y1:y2+1] #Crop the image using the co-ordinates

        #plt.imshow(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)) #show the cropped image

        reader = easyocr.Reader(['en']) #create an easyocr reader object with english as the language
        output = reader.readtext(cropped_image) #read text from the cropped image
        
        f1 = 0
        f2 = 0
        s = ""

        for out in output:
            _, text, text_score = out
            s+=text
        
        numbers = "1234567890"
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        
        for i in numbers:
            if i in s:
                f1 = 1
                break
        for i in chars:
            if i in s:
                f2 = 1
                break
        
        if f1 and f2:
            
            for out in output:
                _, text, text_score = out
                print(text)

            plt.figure()
            plt.imshow(cv2.cvtColor(bfilter, cv2.COLOR_BGR2RGB)) #show processed image

            plt.figure()
            plt.imshow(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)) #show the cropped image

            plt.show()
        else:
            reader = easyocr.Reader(['en']) #create an easyocr reader object with english as the language
            output = reader.readtext(gray)
            for out in output:
                _, text, text_score = out
                print(text)

            plt.figure()
            plt.imshow(cv2.cvtColor(bfilter, cv2.COLOR_BGR2RGB))

            # plt.figure()
            # plt.imshow(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)) #show the cropped image

            # plt.show()