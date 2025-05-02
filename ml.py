#!/usr/bin/env python3

import jetson_inference
import jetson_utils

import cv2

FULL_RGB = None

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        sock.close()
        cv2.destroyAllWindows()
        sys.exit(0)

def process(im):
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
