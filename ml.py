#!/usr/bin/env python3

import cv2
from filterpy.kalman import KalmanFilter
import math
import numpy as np
import pwm
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

FPS = 25

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

GRAPH_SIZE_CHARS = 100

DECAY_EXTREMA = 0.001
DONT_DECAY_EXTREMA = 1. - DECAY_EXTREMA
EXPAND_EXTREMA = 10 * DECAY_EXTREMA
EXTREMA_BROW_L = (0.25, 0.5)
EXTREMA_BROW_R = (0.25, 0.5)
EXTREMA_MOUTH = (0., 0.5)

NARROW_RANGE = 0.1
INV_NARROW = 1. - NARROW_RANGE

def send_to_servos(brow_l, brow_r, mouth):
    pwm.set_rotation(0, 0.25 + 0.25 * brow_l)
    pwm.set_rotation(1, 0.75 - 0.25 * brow_r)
    pwm.set_rotation(2, 0.25 - 0.25 * mouth)

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        exit(0)

def point2np(point):
    return np.array([point.x, point.y], dtype="float32")

def proj_onto_axis(a, b):
    return a.dot(b) / b.dot(b)

def clamp_to_unit(x):
    if x < 0.:
        return 0.
    if x > 1.:
        return 1.
    return x

def update_extrema(running, new_observation, name):
    # if running is None:
    #     return (new_observation, new_observation)
    running_min, running_max = running
    running_min, running_max = (
        DONT_DECAY_EXTREMA * running_min + DECAY_EXTREMA * running_max,
        DONT_DECAY_EXTREMA * running_max + DECAY_EXTREMA * running_min,
    )
    running_range = running_max - running_min
    if running_range < 0.01:
        running_range = 0.01
    if new_observation < running_min:
        new_running_min = running_min - EXPAND_EXTREMA * running_range
        # print(f"Expanding running minimum of the {name} from {running_min} to {new_running_min}")
        running_min = new_running_min
    elif new_observation > running_max:
        new_running_max = running_max + EXPAND_EXTREMA * running_range
        # print(f"Expanding running maximum of the {name} from {running_max} to {new_running_max}")
        running_max = new_running_max

    return (running_min, running_max)

def within_extrema(extrema, observation):
    extreme_min, extreme_max = extrema
    relative_min = INV_NARROW * extreme_min + NARROW_RANGE * extreme_max
    relative_max = INV_NARROW * extreme_max + NARROW_RANGE * extreme_min
    relative_range = relative_max - relative_min
    if relative_range > 0.001:
        return clamp_to_unit((observation - relative_min) / relative_range)

GRAPH_TEXT_LENGTH = None
def graph(name, value):
    global GRAPH_TEXT_LENGTH
    strlen = len(name)
    if GRAPH_TEXT_LENGTH is None or strlen > GRAPH_TEXT_LENGTH:
        GRAPH_TEXT_LENGTH = strlen
    else:
        for _ in range(strlen, GRAPH_TEXT_LENGTH):
            name = " " + name

    # if value is None:
    #     graph = "n/a"
    # else:
    graph = ""
    quantized = int(GRAPH_SIZE_CHARS * clamp_to_unit(value))
    for _ in range(0, quantized):
        graph = graph + "%"
    for _ in range(quantized, GRAPH_SIZE_CHARS):
        graph = graph + " "

    print(f"{name}: [{graph}] ({value})")

def kalman_init():
    kf = KalmanFilter(dim_x=4, dim_z=2) # [x, y, vx, vy]
    dt = 1.0 / FPS

    # State transition matrix
    kf.F = np.array([
        [1,  0,  dt, 0 ],
        [0,  1,  0,  dt],
        [0,  0,  1,  0 ],
        [0,  0,  0,  1 ]
    ])

    # Measurement function: we only observe position (x, y)
    kf.H = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0]
    ])

    kf.R *= 32.0 # 5.0   # Measurement noise: increase if jitter remains
    kf.P *= 10.0  # Initial estimate uncertainty
    kf.Q *= 16.0 # 0.01  # Process noise (tune for smoothness vs. reactivity): decrease if lags behind motion

    return kf

KALMAN_NOSE_TOP = kalman_init()
KALMAN_NOSE_BASE = kalman_init()
KALMAN_BROW_L = kalman_init()
KALMAN_BROW_R = kalman_init()
KALMAN_LIP_LOWER = kalman_init()
KALMAN_LIP_UPPER = kalman_init()

def kalman_update(kalman, observation):
    print()
    kalman.predict()
    kalman.update(observation)
    return kalman.x[:2, 0]

def process(bgr):
    global DLIB_FACE_DETECTOR
    global DLIB_LANDMARK_PREDICTOR
    global FACE_BBOX
    global FACE_BBOX_LAST_UPDATE
    global EXTREMA_BROW_L
    global EXTREMA_BROW_R
    global EXTREMA_MOUTH
    global KALMAN_NOSE_TOP
    global KALMAN_NOSE_BASE
    global KALMAN_BROW_L
    global KALMAN_BROW_R
    global KALMAN_LIP_LOWER
    global KALMAN_LIP_UPPER

    height, width, channels = bgr.shape
    print(bgr.shape)

    # Convert to grayscale:
    im = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    face_bbox_staleness = 42. # a lot
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
            send_to_servos(0.5, 0.5, 0.5)
            show(bgr)
            return

        if face_bbox_updated:
            if FACE_BBOX_LAST_UPDATE is None or face_bbox_staleness > 2.:
                FACE_BBOX_LAST_UPDATE = time.time()
                face_bbox_staleness = 0.
            else:
                FACE_BBOX_LAST_UPDATE = FACE_BBOX_LAST_UPDATE + FACE_BBOX_UPDATE_PERIOD_SECONDS
                face_bbox_staleness = face_bbox_staleness - 1.

    landmarks = DLIB_LANDMARK_PREDICTOR(im, FACE_BBOX)

    nose_top = kalman_update(KALMAN_NOSE_TOP, point2np(landmarks.part(27)))
    nose_base = kalman_update(KALMAN_NOSE_BASE, point2np(landmarks.part(33)))
    brow_left_right = kalman_update(KALMAN_BROW_L, point2np(landmarks.part(20)))
    brow_right_left = kalman_update(KALMAN_BROW_R, point2np(landmarks.part(23)))
    lip_lower_center = kalman_update(KALMAN_LIP_LOWER, point2np(landmarks.part(66)))
    lip_upper_center = kalman_update(KALMAN_LIP_UPPER, point2np(landmarks.part(62)))

    nose_axis = nose_top - nose_base
    standardized_face_size = np.linalg.norm(nose_axis)
    brow_l = proj_onto_axis(brow_left_right - nose_top, nose_axis)
    brow_r = proj_onto_axis(brow_right_left - nose_top, nose_axis)
    mouth = proj_onto_axis(lip_upper_center - lip_lower_center, nose_axis)

    if face_bbox_staleness < 1.:
        EXTREMA_BROW_L = update_extrema(EXTREMA_BROW_L, brow_l, "left brow")
        EXTREMA_BROW_R = update_extrema(EXTREMA_BROW_R, brow_r, "right brow")
        EXTREMA_MOUTH = update_extrema(EXTREMA_MOUTH, mouth, "mouth")

    brow_l = within_extrema(EXTREMA_BROW_L, brow_l)
    brow_r = within_extrema(EXTREMA_BROW_R, brow_r)
    mouth = within_extrema(EXTREMA_MOUTH, mouth)

    if face_bbox_staleness < 2.:
        send_to_servos(brow_l, brow_r, mouth)

    print()
    # print(f"Brow raise (L) min: {EXTREMA_BROW_L[0]}")
    # print(f"Brow raise (L) max: {EXTREMA_BROW_L[1]}")
    # print(f"Brow raise (R) min: {EXTREMA_BROW_R[0]}")
    # print(f"Brow raise (R) max: {EXTREMA_BROW_R[1]}")
    # print(f"         Mouth min: {EXTREMA_MOUTH[0]}")
    # print(f"         Mouth max: {EXTREMA_MOUTH[1]}")
    print(f"Standardized face size: {standardized_face_size}")
    graph("Brow raise (L)", brow_l)
    graph("Brow raise (R)", brow_r)
    graph("Mouth open", mouth)

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

    if DISPLAY_RELEVANT_FACE_LINES:

        brow_left_farleft = point2np(landmarks.part(17))
        brow_left_left = point2np(landmarks.part(18))
        brow_left_center = point2np(landmarks.part(19))
        brow_left_farright = point2np(landmarks.part(21))

        brow_right_farleft = point2np(landmarks.part(22))
        brow_right_center = point2np(landmarks.part(24))
        brow_right_right = point2np(landmarks.part(25))
        brow_right_farright = point2np(landmarks.part(26))

        lip_lower_left = point2np(landmarks.part(67))
        lip_lower_right = point2np(landmarks.part(65))

        mouth_corner_left = point2np(landmarks.part(60))
        mouth_corner_right = point2np(landmarks.part(64))

        lip_upper_left = point2np(landmarks.part(61))
        lip_upper_right = point2np(landmarks.part(63))

        nose_tip = point2np(landmarks.part(30))

        cv2.line(bgr, (int(brow_left_farleft[0] * multiplier), int(brow_left_farleft[1] * multiplier)), (int(brow_left_left[0] * multiplier), int(brow_left_left[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_left_left[0] * multiplier), int(brow_left_left[1] * multiplier)), (int(brow_left_center[0] * multiplier), int(brow_left_center[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_left_center[0] * multiplier), int(brow_left_center[1] * multiplier)), (int(brow_left_right[0] * multiplier), int(brow_left_right[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_left_right[0] * multiplier), int(brow_left_right[1] * multiplier)), (int(brow_left_farright[0] * multiplier), int(brow_left_farright[1] * multiplier)), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (int(brow_right_farleft[0] * multiplier), int(brow_right_farleft[1] * multiplier)), (int(brow_right_left[0] * multiplier), int(brow_right_left[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_right_left[0] * multiplier), int(brow_right_left[1] * multiplier)), (int(brow_right_center[0] * multiplier), int(brow_right_center[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_right_center[0] * multiplier), int(brow_right_center[1] * multiplier)), (int(brow_right_right[0] * multiplier), int(brow_right_right[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(brow_right_right[0] * multiplier), int(brow_right_right[1] * multiplier)), (int(brow_right_farright[0] * multiplier), int(brow_right_farright[1] * multiplier)), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (int(mouth_corner_left[0] * multiplier), int(mouth_corner_left[1] * multiplier)), (int(lip_lower_left[0] * multiplier), int(lip_lower_left[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_lower_left[0] * multiplier), int(lip_lower_left[1] * multiplier)), (int(lip_lower_center[0] * multiplier), int(lip_lower_center[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_lower_center[0] * multiplier), int(lip_lower_center[1] * multiplier)), (int(lip_lower_right[0] * multiplier), int(lip_lower_right[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_lower_right[0] * multiplier), int(lip_lower_right[1] * multiplier)), (int(mouth_corner_right[0] * multiplier), int(mouth_corner_right[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(mouth_corner_right[0] * multiplier), int(mouth_corner_right[1] * multiplier)), (int(lip_upper_right[0] * multiplier), int(lip_upper_right[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_upper_right[0] * multiplier), int(lip_upper_right[1] * multiplier)), (int(lip_upper_center[0] * multiplier), int(lip_upper_center[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_upper_center[0] * multiplier), int(lip_upper_center[1] * multiplier)), (int(lip_upper_left[0] * multiplier), int(lip_upper_left[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(lip_upper_left[0] * multiplier), int(lip_upper_left[1] * multiplier)), (int(mouth_corner_left[0] * multiplier), int(mouth_corner_left[1] * multiplier)), (255, 0, 0), (w + 511) // 512)

        # cv2.line(bgr, (int(nose_top[0] * multiplier), int(nose_top[1] * multiplier)), (int(nose_tip[0] * multiplier), int(nose_tip[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        # cv2.line(bgr, (int(nose_tip[0] * multiplier), int(nose_tip[1] * multiplier)), (int(nose_base[0] * multiplier), int(nose_base[1] * multiplier)), (255, 0, 0), (w + 511) // 512)

        cv2.line(bgr, (int(nose_top[0] * multiplier), int(nose_top[1] * multiplier)), (int(nose_tip[0] * multiplier), int(nose_tip[1] * multiplier)), (255, 0, 0), (w + 511) // 512)
        cv2.line(bgr, (int(nose_tip[0] * multiplier), int(nose_tip[1] * multiplier)), (int(nose_base[0] * multiplier), int(nose_base[1] * multiplier)), (255, 0, 0), (w + 511) // 512)

    show(bgr)
