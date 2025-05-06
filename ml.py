#!/usr/bin/env python3

import cv2
import math
import numpy as np
import time

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
LOG_DISPLAY_UPSCALE = 2

FACE_BBOX = None
FACE_BBOX_LAST_UPDATE = None
FACE_BBOX_UPDATE_PERIOD_SECONDS = 0.5

DISPLAY_FACE_BBOX = True
DISPLAY_ALL_FACE_POINTS = False
DISPLAY_RELEVANT_FACE_LINES = True

NOSE_TOP = None
NOSE_BASE = None

GRAPH_SIZE_CHARS = 100

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        exit(0)

def point2np(point):
    return np.array([point.x, point.y])

def proj_onto_axis(a, b):
    return a.dot(b) / b.dot(b)

def clamp_to_unit(x):
    if x < 0.:
        return 0.
    if x > 1.:
        return 1.
    return x

GRAPH_TEXT_LENGTH = None
def graph(name, value):
    global GRAPH_TEXT_LENGTH
    strlen = len(name)
    if GRAPH_TEXT_LENGTH is None or strlen > GRAPH_TEXT_LENGTH:
        GRAPH_TEXT_LENGTH = strlen
    else:
        for _ in range(strlen, GRAPH_TEXT_LENGTH):
            name = " " + name

    graph = ""
    for _ in range(0, int(GRAPH_SIZE_CHARS * clamp_to_unit(value))):
        graph = graph + "%"
    print(f"{name}: {graph}   ({value})")

def process(bgr):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR
    global FACE_BBOX
    global FACE_BBOX_LAST_UPDATE
    global NOSE_TOP
    global NOSE_BASE

    height, width, channels = bgr.shape

    # Convert to grayscale:
    im = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    update_face_bbox = (FACE_BBOX_LAST_UPDATE is None)
    if not update_face_bbox:
        face_bbox_staleness = (time.time() - FACE_BBOX_LAST_UPDATE) / FACE_BBOX_UPDATE_PERIOD_SECONDS
        if face_bbox_staleness >= 1.:
            update_face_bbox = True

    if update_face_bbox:
        face_bbox_updated = False
        face_bboxes = DLIB_FACE_DETECTOR(im, SCALE_UP_BEFORE_DETECTING_FACES)
        for i, bbox in enumerate(face_bboxes):
            face_bbox_updated = True
            FACE_BBOX = bbox

        if FACE_BBOX is None:
            print("Waiting to detect a face...")
            return

        if face_bbox_updated:
            if FACE_BBOX_LAST_UPDATE is None or face_bbox_staleness > 2.:
                FACE_BBOX_LAST_UPDATE = time.time()
                face_bbox_staleness = 0.
            else:
                FACE_BBOX_LAST_UPDATE = FACE_BBOX_LAST_UPDATE + FACE_BBOX_UPDATE_PERIOD_SECONDS
                face_bbox_staleness = face_bbox_staleness - 1.

    landmarks = DLIB_LANDMARK_PREDICTOR(im, FACE_BBOX)

    multiplier = 1
    for _ in range(0, LOG_DISPLAY_UPSCALE):
        bgr = cv2.pyrUp(bgr)
        multiplier = 2 * multiplier

    if DISPLAY_FACE_BBOX:
        x, y = FACE_BBOX.left() * multiplier, FACE_BBOX.top() * multiplier
        w = (FACE_BBOX.right() * multiplier) - x
        if face_bbox_staleness > 1.:
            face_bbox_staleness = 1.
        color = (0, int(255. * (1. - face_bbox_staleness)), int(255. * face_bbox_staleness))
        cv2.rectangle(bgr, (x, y), (FACE_BBOX.right() * multiplier, FACE_BBOX.bottom() * multiplier), color, (w + 511) // 512)
        cv2.putText(bgr, "Face", (x, y - ((w + 127) // 128)), cv2.FONT_HERSHEY_SIMPLEX, w / 512., color, (w + 511) // 512)

    if DISPLAY_ALL_FACE_POINTS:
        for i, point in enumerate(landmarks.parts()):
            x = point.x * multiplier
            y = point.y * multiplier
            m = (multiplier + 1) // 2 # `+ 1` just so this is not 0 when m = 1
            cv2.circle(bgr, (x, y), m, (255, 0, 0), -1)
            cv2.putText(bgr, f"{i}", (x, y - m), cv2.FONT_HERSHEY_SIMPLEX, w / 1024., (0, 255, 0), (w + 1023) // 1024)

    eyebrow_left_center = point2np(landmarks.part(19))
    eyebrow_right_center = point2np(landmarks.part(24))
    lip_lower_center = point2np(landmarks.part(66))
    lip_upper_center = point2np(landmarks.part(62))
    nose_top = point2np(landmarks.part(27))
    nose_base = point2np(landmarks.part(33))

    NOSE_TOP = nose_top if NOSE_TOP is None else (0.9 * NOSE_TOP + 0.1 * nose_top)
    NOSE_BASE = nose_base if NOSE_BASE is None else (0.9 * NOSE_BASE + 0.1 * nose_base)
    nose_axis = NOSE_TOP - NOSE_BASE

    standardized_face_size = np.linalg.norm(nose_axis)
    eyebrow_raise_l = clamp_to_unit(6. * (proj_onto_axis(eyebrow_left_center - NOSE_TOP, nose_axis) - 0.3))
    eyebrow_raise_r = clamp_to_unit(6. * (proj_onto_axis(eyebrow_right_center - NOSE_TOP, nose_axis) - 0.3))
    mouth_open = clamp_to_unit(2. * (proj_onto_axis(lip_upper_center - lip_lower_center, nose_axis) - 0.05))

    print()
    print(f"Standardized face size: {standardized_face_size}")
    graph("Eyebrow raise (L)", eyebrow_raise_l)
    graph("Eyebrow raise (R)", eyebrow_raise_r)
    graph("Mouth open", mouth_open)

    if DISPLAY_RELEVANT_FACE_LINES:

        eyebrow_left_farleft = point2np(landmarks.part(17))
        eyebrow_left_left = point2np(landmarks.part(18))
        eyebrow_left_right = point2np(landmarks.part(20))
        eyebrow_left_farright = point2np(landmarks.part(21))

        eyebrow_right_farleft = point2np(landmarks.part(22))
        eyebrow_right_left = point2np(landmarks.part(23))
        eyebrow_right_right = point2np(landmarks.part(25))
        eyebrow_right_farright = point2np(landmarks.part(26))

        lip_lower_left = point2np(landmarks.part(67))
        lip_lower_right = point2np(landmarks.part(65))

        mouth_corner_left = point2np(landmarks.part(60))
        mouth_corner_right = point2np(landmarks.part(64))

        lip_upper_left = point2np(landmarks.part(61))
        lip_upper_right = point2np(landmarks.part(63))

        nose_tip = point2np(landmarks.part(30))

        cv2.line(bgr, (eyebrow_left_farleft[0] * multiplier, eyebrow_left_farleft[1] * multiplier), (eyebrow_left_left[0] * multiplier, eyebrow_left_left[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_left[0] * multiplier, eyebrow_left_left[1] * multiplier), (eyebrow_left_center[0] * multiplier, eyebrow_left_center[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_center[0] * multiplier, eyebrow_left_center[1] * multiplier), (eyebrow_left_right[0] * multiplier, eyebrow_left_right[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_right[0] * multiplier, eyebrow_left_right[1] * multiplier), (eyebrow_left_farright[0] * multiplier, eyebrow_left_farright[1] * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (eyebrow_right_farleft[0] * multiplier, eyebrow_right_farleft[1] * multiplier), (eyebrow_right_left[0] * multiplier, eyebrow_right_left[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_left[0] * multiplier, eyebrow_right_left[1] * multiplier), (eyebrow_right_center[0] * multiplier, eyebrow_right_center[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_center[0] * multiplier, eyebrow_right_center[1] * multiplier), (eyebrow_right_right[0] * multiplier, eyebrow_right_right[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_right[0] * multiplier, eyebrow_right_right[1] * multiplier), (eyebrow_right_farright[0] * multiplier, eyebrow_right_farright[1] * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (mouth_corner_left[0] * multiplier, mouth_corner_left[1] * multiplier), (lip_lower_left[0] * multiplier, lip_lower_left[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_left[0] * multiplier, lip_lower_left[1] * multiplier), (lip_lower_center[0] * multiplier, lip_lower_center[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_center[0] * multiplier, lip_lower_center[1] * multiplier), (lip_lower_right[0] * multiplier, lip_lower_right[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_right[0] * multiplier, lip_lower_right[1] * multiplier), (mouth_corner_right[0] * multiplier, mouth_corner_right[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (mouth_corner_right[0] * multiplier, mouth_corner_right[1] * multiplier), (lip_upper_right[0] * multiplier, lip_upper_right[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_right[0] * multiplier, lip_upper_right[1] * multiplier), (lip_upper_center[0] * multiplier, lip_upper_center[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_center[0] * multiplier, lip_upper_center[1] * multiplier), (lip_upper_left[0] * multiplier, lip_upper_left[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_left[0] * multiplier, lip_upper_left[1] * multiplier), (mouth_corner_left[0] * multiplier, mouth_corner_left[1] * multiplier), (255, 0, 0), (w + 511) // 512)

        # cv2.line(bgr, (nose_top[0] * multiplier, nose_top[1] * multiplier), (nose_tip[0] * multiplier, nose_tip[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        # cv2.line(bgr, (nose_tip[0] * multiplier, nose_tip[1] * multiplier), (nose_base[0] * multiplier, nose_base[1] * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (int(NOSE_TOP[0]) * multiplier, int(NOSE_TOP[1]) * multiplier), (nose_tip[0] * multiplier, nose_tip[1] * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (nose_tip[0] * multiplier, nose_tip[1] * multiplier), (int(NOSE_BASE[0]) * multiplier, int(NOSE_BASE[1]) * multiplier), (255, 0, 0), (w + 511) // 512)

    show(bgr)
