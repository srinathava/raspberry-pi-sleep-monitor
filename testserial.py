#!/usr/bin/python
import glob
from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from ProcessProtocolUtils import TerminalEchoProcessProtocol

devices = glob.glob('/dev/ttyUSB*')
SerialPort(TerminalEchoProcessProtocol(), devices[0], reactor, timeout=3)

reactor.run()
