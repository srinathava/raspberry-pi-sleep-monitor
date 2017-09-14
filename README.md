# A baby sleep monitor using a Raspberry Pi

This setup shows how to create a baby sleep monitor which is able to stream a low latency image stream from a Raspberry Pi to a computer with some additional features:

1. Motion detection to detect when the baby wakes up.
2. It also works with a Massimo oximeter to monitor O2 and heart rate sats.

## Setup
## Upgrade Raspberry Pi

Depending on how old your Raspberry Pi is, you might need to do an apt-get
update/upgrade in order to be able to compile Janus (which is not available
on apt as of this writing). On a terminal:

    sudo apt-get update
    sudo apt-get upgrade
    
This takes a while, so be patient.

## Setup Raspberry Pi Camera

First enable Raspberry Pi in the firmware:

    sudo raspi-config
    # Once the UI comes up, select the following options
    # Choose (5) Interfacing options
    # Choose (P1) Camera
    # Choose <Yes>
    # Finish

Now enable the Raspberry Pi Camera to work like a standard Linux video
webcam:

    sudo nano /etc/rc.local
    # Put the following line just before exit(0)
    sudo modprobe bcm2835-v4l2

(Optional) Disable the bright red LED

    sudo nano /boot/config.txt
    # Add the following line to the end:
    disable_camera_led=1

## Disable console login over serial

In order to read the Masimo oximeter using a serial to USB cable, you need to disable console login over serial. To do this:

    sudo raspi-config
    # Choose Interfacing Options > Serial
    # Choose <No> For "Should login shell be accessible over serial?"
    # Choose <Yes> for "Would you like serial port hardware to be enabled?"

## Download and build the sleep monitor code

Now download and build this repo. 

**NOTE**: The build.sh script below will modify /etc/rc.local etc. Please give it a quick read if you are uncertain.

     cd ~
     mkdir code && code code
     git clone https://github.com/srinathava/raspberry-pi-stream-sleep-monitor.git
     cd raspberry-pi-sleep-monitor
     ./build.sh
     
Reboot. Note that the sleep monitor will automatically start after a reboot because /etc/rc.local is modified to automatically invoke it.

## Use a browser

Now from any other computer in the local network, navigate to:

     http://ip.of.your.rpi/

*TODO*: It would be nice to have a script which automatically figures out the IP address of the Raspberry Pi on the local network so you do not have to hunt for it after reboots/IP address changes.
