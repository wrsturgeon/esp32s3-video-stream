#!/usr/bin/env python3

# change frequency for changing the output and fixed pwm value.
import i2cdev
import math
import numpy as np
import time

pwm = i2cdev.I2C(0x40, 1) # (PCA9685 address, I2C bus)

# Reset PWM
pwm.write(bytes([0xFA, 0]))     # zero all pin
pwm.write(bytes([0xFB, 0]))     # zero all pin
pwm.write(bytes([0xFC, 0]))     # zero all pin
pwm.write(bytes([0xFD, 0]))     # zero all pin
pwm.write(bytes([0x01, 0x04]))  # The 16 LEDn outputs are configured with a totem pole structure.
pwm.write(bytes([0x00, 0x01]))  #PCA9685 responds to LED All Call I2C-bus address
time.sleep(0.01)  # wait for oscillator

'''
Set the PWM frequency to the provided value in hertz.
The maximum PWM frequency is 1526 Hz if the PRE_SCALE register is set "0x03h".
The minimum PWM frequency is 24 Hz if the PRE_SCALE register is set "0xFFh".
he PRE_SCALE register can only be set when the SLEEP bit of MODE1 register is set to logic 1.
'''

# Program to set the Duty cycle and frequency of PWM.
freq_hz = 50 # Frequency of PWM 
freq_hz = freq_hz * 0.9 # correction
prescale = int(25000000.0/(4096.0*float(freq_hz))-1) # datasheet equation
pwm.write(bytes([0x00, 0x10]))
time.sleep(0.01)
pwm.write(bytes([0xFE, prescale]))
pwm.write(bytes([0x00, 0x80]))
time.sleep(0.01)
pwm.write(bytes([0x00, 0x00]))
time.sleep(0.01)
pwm.write(bytes([0x01, 0x04]))
time.sleep(0.01)

# Period is 20ms (frequency is 50Hz).
# We want 1ms to represent 0.00... and 2ms to represent 1.00...
# We have 12 bits to work with: [0, 4096)
# So 1ms is (1/20)(4096) = 204.8 ~= 205
#  & 2ms is (2/20)(4096) = 409.6 ~= 410

# Program to set the PWM for the channel.
def set_rotation(channel, unit_all_the_way_around):
    assert unit_all_the_way_around >= 0.
    assert unit_all_the_way_around <= 1.

    quantized = int(204.8 * (1. + unit_all_the_way_around))
    assert quantized >= 0
    assert quantized <= 4095

    LED0__ON_L         = 0x06
    LED0__ON_H         = 0x07
    LED0_OFF_L         = 0x08
    LED0_OFF_H         = 0x09
    pwm.write(bytes([(LED0__ON_L + 4 * channel), 0]))
    pwm.write(bytes([(LED0__ON_H + 4 * channel), 0]))
    pwm.write(bytes([(LED0_OFF_L + 4 * channel), (quantized & 0xFF)]))
    pwm.write(bytes([(LED0_OFF_H + 4 * channel), (quantized >> 8)]))
    # time.sleep(0.01)

while True:
    x = 0.25 + 0.1 * math.sin(2. * time.time())
    set_rotation(0, x)
