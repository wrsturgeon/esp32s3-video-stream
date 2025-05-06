#!/usr/bin/env python3.8

print("Importing Adafruit's PCA9685 servo library...")
from adafruit_servokit import ServoKit

print("Initializing the PCA9685 to work with servos...")
pca9685 = ServoKit(channels=16)

def move(i, angle):
    print(f"Sending servo #{i} to {angle} degrees...")
    pca9685.servo[i].angle = angle

move(0, 90)

import time
t = time.time()
while True:

    t += 1
    while time.time() < t:
        pass
    move(0, 80)

    t += 1
    while time.time() < t:
        pass
    move(0, 100)
