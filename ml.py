#!/usr/bin/env python3

import jetson_inference
import jetson_utils

import cv2

def show(im):
            cv2.imshow('Livestream', im)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                sock.close()
                cv2.destroyAllWindows()
                sys.exit(0)
