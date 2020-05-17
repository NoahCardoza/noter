import os
import cv2
import numpy as np
import logging

log = logging.getLogger('cv')

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')


def detect_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return len(faces)


def capture_slide(img):
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
    # invert = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    cnts = sorted(contours, key=cv2.contourArea, reverse=True)

    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        return img[y:y + h, x:x + w]


def mse(image1, image2):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension

    is1 = image1.shape
    is2 = image2.shape

    if is1[0] * is1[1] < is2[0] * is2[1]:
        image2 = image2[0:is1[0], 0:is1[1]]
    else:
        image1 = image1[0:is2[0], 0:is2[1]]

    err = np.sum((image1.astype("float") - image2.astype("float")) ** 2)
    err /= float(image1.shape[0] * image1.shape[1])

    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err


def strip_slides(filename):
    vid = cv2.VideoCapture(filename)
    slides = []

    crop_slides = False
    success, image = vid.read()
    if detect_faces(image):
        crop_slides = True

    seconds = 5
    fps = vid.get(cv2.CAP_PROP_FPS)

    multiplier = int(fps * seconds)
    last_slid = None

    if crop_slides:
        slid = capture_slide(image)
    else:
        slid = image

    slides.append(slid)
    last_slid = slid

    log.info('starting slide search')

    while success:
        frameId = int(round(vid.get(1)))
        success, image = vid.read()
        if not frameId % multiplier:
            if crop_slides:
                slid = capture_slide(image)
            else:
                slid = image

            if mse(slid, last_slid) > 100:
                log.info('found new slide')
                slides.append(slid)
        last_slid = slid

    vid.release()

    log.info('processes whole video')

    return slides


# vid = cv2.VideoCapture("c931b9b5-103a-4cbf-9104-95533315269f.mkv")
# for i, slid in enumerate(strip_slides(vid)):
#     path = "frames/frame-%d.jpg" % i
#     cv2.imwrite(path, slid)
# vid.release()


# for file in os.listdir('frames'):
#     img = cv2.imread(f'frames/{file}')
#     blur = cv2.GaussianBlur(img, (5, 5), 0)
#     gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
#     invert = cv2.bitwise_not(gray)
#     _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

#     contours, hier = cv2.findContours(
#         thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

#     cnts = sorted(contours, key=cv2.contourArea, reverse=True)[:2]

#     height, width, depth = img.shape

#     for cnt in cnts:
#         x, y, w, h = cv2.boundingRect(cnt)
#         if w > width / 2 and h < 10:
#             print(x, y, w, h)
#             cv2.drawContours(img, [cnt], 0, (0, 255, 0), 2)
#         # cv2.drawContours(mask, [cnt], 0, 255, -1)

#     cv2.imshow('ROI', img)
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
