#!/usr/bin/env python3

import jetson_inference
import jetson_utils

import cv2

import dlib
assert(dlib.DLIB_USE_CUDA)
assert(dlib.cuda.get_num_devices() > 0)

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

FULL_RGB = None

SCALE_UP_BEFORE_DETECTING_FACES = 0
LOG_IMAGE_UPSCALE = 2

FACE_BBOX = None

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        exit(0)

def process(im):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR
    global FACE_BBOX

    height, width, channels = im.shape

    # Convert to grayscale:
    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    new_bbox = False
    face_bboxes = DLIB_FACE_DETECTOR(im, SCALE_UP_BEFORE_DETECTING_FACES)
    for i, bbox in enumerate(face_bboxes):
        new_bbox = True
        FACE_BBOX = bbox

    if FACE_BBOX is None:
        return

    x, y = FACE_BBOX.left(), FACE_BBOX.top()
    cv2.rectangle(im, (x, y), (FACE_BBOX.right(), FACE_BBOX.bottom()), (0, 255, 0), 2)
    cv2.putText(im, f"Face #{i + 1}", (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if new_bbox else (255, 0, 0), 2)

    # left = 0
    # top = 0
    # right = width
    # bottom = height
    # bbox = dlib.rectangle(left, top, right, bottom)

    predicted = DLIB_LANDMARK_PREDICTOR(im, FACE_BBOX)

    multiplier = 1
    for _ in range(0, LOG_IMAGE_UPSCALE):
        im = cv2.pyrUp(im)
        multiplier = 2 * multiplier

    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)

    for i, point in enumerate(predicted.parts()):
        x = point.x * multiplier
        y = point.y * multiplier
        cv2.circle(im, (x, y), multiplier, (0, 0, 255), -1)
        cv2.putText(im, f"{i + 1}", (x - multiplier, y - multiplier), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    show(im)

def to_cuda_test(im):
    # fucking python fuckery
    global FULL_RGB

    # Copy from CPU to GPU:
    bgr = jetson_utils.cudaFromNumpy(im, isBGR=True)

    # Allocate the RGB buffer if we haven't already,
    # but use the image shape we actually get
    # for flexibility w.r.t. future changes:
    if FULL_RGB is None:
        FULL_RGB = jetson_utils.cudaAllocMapped(height=bgr.height, width=bgr.width, format='rgb8')

    # Convert from BGR to RGB (since OpenCV outputs BGR by default):
    jetson_utils.cudaConvertColor(bgr, FULL_RGB)

    # Wait for the GPU to finish processing shared memory:
    jetson_utils.cudaDeviceSynchronize()

    exit()
