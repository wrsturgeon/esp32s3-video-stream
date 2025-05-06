#!/usr/bin/env python3

import cv2
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
LOG_DISPLAY_UPSCALE = 0

FACE_BBOX = None
FACE_BBOX_LAST_UPDATE = None
FACE_BBOX_UPDATE_PERIOD_SECONDS = 0.5

DISPLAY_FACE_BBOX = True
DISPLAY_ALL_FACE_POINTS = False
DISPLAY_RELEVANT_FACE_LINES = True

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        exit(0)

def distance(a, b):
    dx = b.x - a.x
    dy = b.y - a.y
    sqrt(dx * dx + dy * dy)

def process(bgr):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR
    global FACE_BBOX
    global FACE_BBOX_LAST_UPDATE

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

    eyebrow_left_center = landmarks.part(19)
    eyebrow_right_center = landmarks.part(24)
    lip_lower_center = landmarks.part(66)
    lip_upper_center = landmarks.part(62)
    nose_top = landmarks.part(27)
    nose_base = landmarks.part(33)

    standardized_face_size = distance(nose_top, nose_base)

    print()
    print("Standardized face size: {standardized_face_size}")

    if DISPLAY_RELEVANT_FACE_LINES:

        eyebrow_left_farleft = landmarks.part(17)
        eyebrow_left_left = landmarks.part(18)
        eyebrow_left_right = landmarks.part(20)
        eyebrow_left_farright = landmarks.part(21)

        eyebrow_right_farleft = landmarks.part(22)
        eyebrow_right_left = landmarks.part(23)
        eyebrow_right_right = landmarks.part(25)
        eyebrow_right_farright = landmarks.part(26)

        lip_lower_left = landmarks.part(67)
        lip_lower_right = landmarks.part(65)

        mouth_corner_left = landmarks.part(60)
        mouth_corner_right = landmarks.part(64)

        lip_upper_left = landmarks.part(61)
        lip_upper_right = landmarks.part(63)

        nose_tip = landmarks.part(30)

        cv2.line(bgr, (eyebrow_left_farleft.x * multiplier, eyebrow_left_farleft.y * multiplier), (eyebrow_left_left.x * multiplier, eyebrow_left_left.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_left.x * multiplier, eyebrow_left_left.y * multiplier), (eyebrow_left_center.x * multiplier, eyebrow_left_center.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_center.x * multiplier, eyebrow_left_center.y * multiplier), (eyebrow_left_right.x * multiplier, eyebrow_left_right.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_left_right.x * multiplier, eyebrow_left_right.y * multiplier), (eyebrow_left_farright.x * multiplier, eyebrow_left_farright.y * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (eyebrow_right_farleft.x * multiplier, eyebrow_right_farleft.y * multiplier), (eyebrow_right_left.x * multiplier, eyebrow_right_left.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_left.x * multiplier, eyebrow_right_left.y * multiplier), (eyebrow_right_center.x * multiplier, eyebrow_right_center.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_center.x * multiplier, eyebrow_right_center.y * multiplier), (eyebrow_right_right.x * multiplier, eyebrow_right_right.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (eyebrow_right_right.x * multiplier, eyebrow_right_right.y * multiplier), (eyebrow_right_farright.x * multiplier, eyebrow_right_farright.y * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (mouth_corner_left.x * multiplier, mouth_corner_left.y * multiplier), (lip_lower_left.x * multiplier, lip_lower_left.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_left.x * multiplier, lip_lower_left.y * multiplier), (lip_lower_center.x * multiplier, lip_lower_center.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_center.x * multiplier, lip_lower_center.y * multiplier), (lip_lower_right.x * multiplier, lip_lower_right.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_lower_right.x * multiplier, lip_lower_right.y * multiplier), (mouth_corner_right.x * multiplier, mouth_corner_right.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (mouth_corner_right.x * multiplier, mouth_corner_right.y * multiplier), (lip_upper_right.x * multiplier, lip_upper_right.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_right.x * multiplier, lip_upper_right.y * multiplier), (lip_upper_center.x * multiplier, lip_upper_center.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_center.x * multiplier, lip_upper_center.y * multiplier), (lip_upper_left.x * multiplier, lip_upper_left.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (lip_upper_left.x * multiplier, lip_upper_left.y * multiplier), (mouth_corner_left.x * multiplier, mouth_corner_left.y * multiplier), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (nose_top.x * multiplier, nose_top.y * multiplier), (nose_tip.x * multiplier, nose_tip.y * multiplier), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (nose_tip.x * multiplier, nose_tip.y * multiplier), (nose_base.x * multiplier, nose_base.y * multiplier), (255, 0, 0), (w + 511) // 512)

    show(bgr)
