from twisted.internet import reactor, stdio
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall
import os
import random
import argparse

from datetime import datetime

from ProcessProtocolUtils import TerminalEchoProcessProtocol, spawnNonDaemonProcess

class RandomizedEmulator:
    def __init__(self):
        self.alarm = 0
        self.BPM = -1
        self.SPO2 = -1
        self.pauseWriteToPort = False

        self.loop = LoopingCall(self.randomize)
        self.loop.start(2)

    def randomize(self):
        self.SPO2 = 100 + random.randint(-10, 0)
        self.BPM = 100 + random.randint(-10, 10)
        if random.randint(0, 100) > 92:
            self.alarm = 1 - self.alarm

        timestr = datetime.now().strftime('%y/%m/%d %H:%M:%S')
        print('%s SPO2=%d%% BPM=%d ALARM=%x\n' % (timestr, self.SPO2, self.BPM, self.alarm))


class UserInputEmulator(basic.LineReceiver):
    delimiter = os.linesep.encode('ASCII')

    def __init__(self):
        self.alarm = 0
        self.BPM = -1
        self.SPO2 = -1
        self.pauseWriteToPort = False

        self.propMap = {'a': 'alarm', 'b': 'BPM', 'o': 'SPO2'}

    def connectionMade(self):
        self.transport.write('**** Key: SPO2: o, BPM: b, alarm: a\n')
        self.transport.write('**** Commands: p: pause, r: resume\n')
        self.transport.write('>>> ')

    def setProp(self, propVal):
        (propName, propValStr) = propVal.split('=')
        propVal = int(propValStr)
        realPropName = self.propMap[propName]
        setattr(self, realPropName, propVal)

    def setProps(self, line):
        line = line.replace(' ', '')
        propVals = line.split(',')
        for propVal in propVals:
            self.setProp(propVal)

    def tryToSetProps(self, line):
        try:
            self.setProps(line)
        except:  # noqa: E722 (OK to use bare except)
            self.transport.write('*** Error interpreting %s  ***\n' % line)

    def lineReceived(self, line):
        print 'recd input line %s' % line
        if line == 'p' or line == 'pause':
            self.pauseWriteToPort = True
        elif line == 'r' or line == 'resume':
            self.pauseWriteToPort = False
        else:
            self.tryToSetProps(line)

        self.transport.write('>>> ')

def writeToSerialPort(serialPort, emulator):
    if not emulator.pauseWriteToPort:
        timestr = datetime.now().strftime('%y/%m/%d %H:%M:%S')
        serialPort.write('%s SPO2=%d%% BPM=%d ALARM=%x\n' % (timestr, emulator.SPO2, emulator.BPM, emulator.alarm))

class SocatProcessProtocol(TerminalEchoProcessProtocol):
    def __init__(self, emulator):
        TerminalEchoProcessProtocol.__init__(self)
        self.emulator = emulator

    def errLineReceived(self, line):
        if 'starting data transfer loop' in line:
            os.system('chmod 777 /dev/ttyUSB0')
            self.serialPort = SerialPort(basic.LineReceiver(), '/dev/ttyToUSB', reactor, timeout=3)
            self.loop = LoopingCall(writeToSerialPort, self.serialPort, self.emulator)
            self.loop.start(2)

parser = argparse.ArgumentParser('Emulator for an oximeter')
parser.add_argument('--interactive', dest='interactive',
                    action='store_true',
                    help='Interactive mode (default is randomized)')
args = parser.parse_args()

if args.interactive:
    emulator = UserInputEmulator()
    stdio.StandardIO(emulator)
else:
    emulator = RandomizedEmulator()

args = r'socat -d -d pty,raw,echo=0,link=/dev/ttyUSB0 pty,raw,echo=0,link=/dev/ttyToUSB'.split()
spawnNonDaemonProcess(reactor, SocatProcessProtocol(emulator), 'socat', args)

reactor.run()
