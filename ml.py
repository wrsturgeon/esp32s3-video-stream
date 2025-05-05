#!/usr/bin/env python3

import jetson_inference
import jetson_utils

import cv2
import dlib

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

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        sock.close()
        cv2.destroyAllWindows()
        sys.exit(0)

def process(im):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR

    face_bboxes = DLIB_FACE_DETECTOR(im, 1)
    print(face_bboxes)
    for i, bbox in enumerate(face_bboxes):
        x, y = bbox.left(), bbox.top()
        cv2.rectangle(im, (x, y), (bbox.right(), bbox.bottom()), (0, 255, 0), 2)
        cv2.putText(im, f"Face #{i + 1}", (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # shape = predictor(im, bbox)
        # shape = shape2np(shape)

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
