#!/usr/bin/python
from time import sleep
import serial
import glob

# Establish the connection on a specific port
devices = glob.glob('/dev/ttyUSB*')
ser = serial.Serial(devices[0], timeout=3)

x = 1 
while True:
   print ser.readline() # Read the newest output 
   x += 1
