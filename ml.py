#!/usr/bin/env python3

import cv2

import dlib
assert dlib.DLIB_USE_CUDA
assert dlib.cuda.get_num_devices() > 0

import pathlib
DLIB_LANDMARK_PREDICTOR_PATH = "dlib_shape_predictor.dat"
if not pathlib.Path(DLIB_LANDMARK_PREDICTOR_PATH).exists():
    import urllib.request
    urllib.request.urlretrieve("http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2", DLIB_LANDMARK_PREDICTOR_PATH + ".bz2")
    import bz2
    zipfile = bz2.BZ2File(DLIB_LANDMARK_PREDICTOR_PATH + ".bz2")
    decompressed = zipfile.read()
    open(DLIB_LANDMARK_PREDICTOR_PATH, 'wb').write(decompressed)

DLIB_FACE_DETECTOR = dlib.get_frontal_face_detector()
DLIB_LANDMARK_PREDICTOR = dlib.shape_predictor(DLIB_LANDMARK_PREDICTOR_PATH)

SCALE_UP_BEFORE_DETECTING_FACES = 0
LOG_DISPLAY_UPSCALE = 3

FACE_BBOX = None
FACE_BBOX_LAST_UPDATE = None

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        exit(0)

def process(im):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR
    global FACE_BBOX
    global FACE_BBOX_LAST_UPDATE

    height, width, channels = im.shape

    # Convert to grayscale:
    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    face_bbox_staleness = time.time() - FACE_BBOX_LAST_UPDATE

    face_bboxes = DLIB_FACE_DETECTOR(im, SCALE_UP_BEFORE_DETECTING_FACES)
    for i, bbox in enumerate(face_bboxes):
        FACE_BBOX = bbox

    if FACE_BBOX is None:
        print("Waiting to detect a face...")
        return

    # left = 0
    # top = 0
    # right = width
    # bottom = height
    # bbox = dlib.rectangle(left, top, right, bottom)

    predicted = DLIB_LANDMARK_PREDICTOR(im, FACE_BBOX)

    multiplier = 1
    for _ in range(0, LOG_DISPLAY_UPSCALE):
        im = cv2.pyrUp(im)
        multiplier = 2 * multiplier

    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)

    x, y = FACE_BBOX.left() * multiplier, FACE_BBOX.top() * multiplier
    w = (FACE_BBOX.right() * multiplier) - x
    color = (0, int(255. * (1. - face_bbox_staleness)), int(255. * face_bbox_staleness))
    cv2.rectangle(im, (x, y), (FACE_BBOX.right() * multiplier, FACE_BBOX.bottom() * multiplier), color, w // 256)
    cv2.putText(im, "Face", (x, y - w // 128), cv2.FONT_HERSHEY_SIMPLEX, w // 512, color, w // 256)

    for i, point in enumerate(predicted.parts()):
        x = point.x * multiplier
        y = point.y * multiplier
        m = (multiplier + 1) // 2 # `+ 1` just so this is not 0 when m = 1
        cv2.circle(im, (x, y), m, (0, 0, 255), -1)
        cv2.putText(im, f"{i}", (x, y - m), cv2.FONT_HERSHEY_SIMPLEX, w // 1024, (0, 255, 0), w // 512)

    show(im)
