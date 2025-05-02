#!/usr/bin/env python3

import jetson.inference
import jetson.utils

def show(im):
            cv2.imshow('Livestream', im)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                sock.close()
                cv2.destroyAllWindows()
                sys.exit(0)
