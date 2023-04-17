#source: https://docs.arduino.cc/tutorials/nicla-vision/getting-started

import pyb # Import module for board related functions
import sensor # Import the module for sensor related functions
import image # Import module containing machine vision algorithms

redLED = pyb.LED(1) # built-in red LED
blueLED = pyb.LED(3) # built-in blue LED
greenLED = pyb.LED(2) # built-in green LED

sensor.reset() # Initialize the camera sensor.
sensor.set_pixformat(sensor.RGB565) # Sets the sensor to RGB
sensor.set_framesize(sensor.QVGA) # Sets the resolution to 320x240 px
sensor.set_vflip(True) # Flips the image vertically
sensor.set_hmirror(True) # Mirrors the image horizontally

redLED.on()
sensor.skip_frames(time = 2000) # Skip some frames to let the image stabilize

redLED.off()
blueLED.on()

print("You're on camera!")
sensor.snapshot().save("example.jpg")

blueLED.off()
print("Done! Reset the camera to see the saved image.")
