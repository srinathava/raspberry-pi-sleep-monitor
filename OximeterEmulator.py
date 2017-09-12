from twisted.internet import reactor, stdio
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall
import os

from datetime import datetime

from ProcessProtocolUtils import TerminalEchoProcessProtocol, spawnNonDaemonProcess

class InputReader(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self):
        self.alarm = 0
        self.BPM = -1
        self.SPO2 = -1
        self.pauseWriteToPort = False

        self.propMap = {'a': 'alarm', 'b': 'BPM', 'o': 'SPO2'};

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
        except:
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

def writeToSerialPort(serialPort, reader):
    if not reader.pauseWriteToPort:
        timestr = datetime.now().strftime('%y/%m/%d %H:%M:%S')
        serialPort.write('%s SPO2=%d%% BPM=%d ALARM=%x\n' % (timestr, reader.SPO2, reader.BPM, reader.alarm))

class SocatProcessProtocol(TerminalEchoProcessProtocol):
    def errLineReceived(self, line):
        if 'starting data transfer loop' in line:
            os.system('chmod 777 /dev/ttyUSB0')

            self.reader = InputReader()
            stdio.StandardIO(self.reader)
            self.serialPort = SerialPort(basic.LineReceiver(), '/dev/ttyToUSB', reactor, timeout=3)
            self.loop = LoopingCall(writeToSerialPort, self.serialPort, self.reader)
            self.loop.start(2)

args = r'socat -d -d pty,raw,echo=0,link=/dev/ttyUSB0 pty,raw,echo=0,link=/dev/ttyToUSB'.split()
spawnNonDaemonProcess(reactor, SocatProcessProtocol(), 'socat', args)

reactor.run()

