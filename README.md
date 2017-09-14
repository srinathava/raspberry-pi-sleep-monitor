# A baby sleep monitor using a Raspberry Pi

This setup shows how to create a baby sleep monitor which is able to stream a low latency image stream from a Raspberry Pi to a computer with some additional features:

1. Motion detection to detect when the baby wakes up.
2. It also works with a Massimo oximeter to monitor O2 and heart rate sats.

## Setup
### Upgrade Raspberry Pi

Depending on how old your Raspberry Pi is, you might need to do an apt-get
update/upgrade in order to be able to compile Janus (which is not available
on apt as of this writing). On a terminal:

    sudo apt-get update
    sudo apt-get upgrade
    
This takes a while, so be patient.

### Setup Raspberry Pi Camera

First enable Raspberry Pi in the firmware:

    sudo raspi-config
    # Once the UI comes up, select the following options
    # Choose (5) Interfacing options
    # Choose (P1) Camera
    # Choose <Yes>
    # Finish

(Optional) Disable the bright red LED

    sudo nano /boot/config.txt
    # Add the following line to the end:
    disable_camera_led=1

### Disable console login over serial

In order to read the Masimo oximeter using a serial to USB cable, you need to disable console login over serial. To do this:

    sudo raspi-config
    # Choose Interfacing Options > Serial
    # Choose <No> For "Should login shell be accessible over serial?"
    # Choose <Yes> for "Would you like serial port hardware to be enabled?"

### Download and build the sleep monitor code

Now download and build this repo. 

**NOTE**: The build.sh script below will modify /etc/rc.local etc. Please give it a quick read if you are uncertain.

     cd ~
     mkdir code && code code
     git clone https://github.com/srinathava/raspberry-pi-stream-sleep-monitor.git
     cd raspberry-pi-sleep-monitor
     ./build.sh
     
Reboot. Note that the sleep monitor will automatically start after a reboot because /etc/rc.local is modified to automatically invoke it.

### Connect the Masimo Rad 8 Oximeter to the Raspberry Pi

You will need to ensure that the serial output format for the Oximeter is set to "AS1". From the manual, this is done by:

    To access Level 3 parameters/measurements, hold down the Enter Button 
    and press the Down Button for 5 seconds. After entering menu Level 3, 
    use the Up or Down button to move between settings.
    
When you see the top panel says "SEr", you will want to press `up` till the bottom panel says `AS1`. Then press `enter` to select that.

**IMPORTANT**: Ensure that you only change this setting. Changing other settings can be a safety hazard and could compromise the functioning of the oximeter.

Now connect the Oximeter to the Raspberry Pi using a serial to USB cable such as ["UGREEN USB 2.0 to RS232 DB9 Serial Cable Male A Converter Adapter..."](https://smile.amazon.com/gp/product/B00QUZY4WO/ref=oh_aui_detailpage_o04_s00?ie=UTF8&psc=1). Although this cable seems to work, I've found it doesn't really tighten nicely to the back of the Oximeter. If you know of a better cable, let me know.

## Using the sleep monitor

Now from any other computer in the local network, navigate to:

     http://ip.of.your.rpi/

*TODO*: It would be nice to have a script which automatically figures out the IP address of the Raspberry Pi on the local network so you do not have to hunt for it after reboots/IP address changes.
