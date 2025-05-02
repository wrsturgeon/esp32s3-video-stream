#!/usr/bin/env python3

import jetson_inference
import jetson_utils

import cv2

FULL_JPEG_BUFFER = None

def show(im):
    cv2.imshow('Livestream', im)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        sock.close()
        cv2.destroyAllWindows()
        sys.exit(0)

def process(im):
    if FULL_JPEG_BUFFER is None:
        FULL_JPEG_BUFFER = jetson_utils.cudaImage(like=im) # jetson_utils.cudaImage(width=160, height=120, format="rgb8")

    # Seems to be (height, width, channels), both in `im` (from OpenCV) and in CUDA.
    jetson_utils.cudaMemcpy(dst=FULL_JPEG_BUFFER, src=im)

    # Wait for the GPU to finish processing shared memory:
    jetson_utils.cudaDeviceSynchronize()

    exit()
