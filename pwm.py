#!/usr/bin/env python3

from adafruit_servokit import ServoKit

pca9685 = ServoKit(channels=16)
pca9685.servo[0].angle = 90
