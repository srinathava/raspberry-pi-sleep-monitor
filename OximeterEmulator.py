from twisted.internet import reactor, stdio
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall

from datetime import datetime

class InputReader(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self):
        self.alarm = 0
        self.BPM = -1
        self.SPO2 = -1

        self.propMap = {'a': 'alarm', 'b': 'BPM', 'o': 'SPO2'};

    def connectionMade(self):
        self.transport.write('Key: SPO2: o, BPM: b, alarm: a\n')
        self.transport.write('>>> ')

    def lineReceived(self, line):
        try:
            (propName, propValStr) = line.split('=')
            propVal = int(propValStr)
            realPropName = self.propMap[propName]
            setattr(self, realPropName, propVal)
        except:
            self.transport.write('*** Error ***\n')

        self.transport.write('>>> ')

def writeToSerialPort(serialPort, reader):
    timestr = datetime.now().strftime('%y/%m/%d %H:%M:%S')
    serialPort.write('%s SPO2=%d%% BPM=%d ALARM=%x\n' % (timestr, reader.SPO2, reader.BPM, reader.alarm))

reader = InputReader()

stdio.StandardIO(reader)

serialPort = SerialPort(basic.LineReceiver(), '/dev/ttyToUSB', reactor, timeout=3)

loop = LoopingCall(writeToSerialPort, serialPort, reader)
loop.start(2)

reactor.run()
