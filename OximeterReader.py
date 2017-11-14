import glob
import re
import os
import dateutil.parser
from datetime import datetime

from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort
from twisted.internet.task import LoopingCall

from MotionStateMachine import MotionStateMachine
from LoggingUtils import log, setupLogging
from Constants import OximeterStatus

class OximeterReadProtocol(LineReceiver):
    # This seemingly unused line is necessary to over-ride the delimiter
    # property of basic.LineReceiver which by default is '\r\n'. Do not
    # remove this!
    delimiter = os.linesep.encode('ASCII')

    PAT_LINE = re.compile(r'(?P<time>\d\d/\d\d/\d\d \d\d:\d\d:\d\d).*SPO2=(?P<SPO2>\d+).*BPM=(?P<BPM>\d+).*ALARM=(?P<alarm>\S+).*')

    def __init__(self, reader):
        self.reader = reader
        self.reactor = reader.reactor
        self.app = reader.app
        self.config = self.app.config
        self.resetTimer = None
        self.badReadCount = 0

        self.reset(OximeterStatus.CABLE_DISCONNECTED, 'init')

    def reset(self, status, asker=''):
        log('resetting with %s (by [%s])' % (status, asker))

        if not status == OximeterStatus.CONNECTED:
            self.SPO2 = -1
            self.BPM = -1
            self.alarm = 0
            self.readTime = datetime.min

        if status == OximeterStatus.CABLE_DISCONNECTED:
            self.badReadCount = 0

        self.motionDetected = False
        self.motionSustained = False
        self.status = status

        self.setLineMode()

        self.alarmStateMachine = MotionStateMachine()
        self.alarmStateMachine.CALM_TIME = 0
        self.alarmStateMachine.SUSTAINED_TIME = self.config.spo2AlarmTime

        self.motionStateMachine = MotionStateMachine()
        self.motionStateMachine.CALM_TIME = self.config.sustainedTime
        self.motionStateMachine.SUSTAINED_TIME = self.config.calmTime

    def lineReceived(self, line):
        m = self.PAT_LINE.match(line.decode('ASCII'))
        if m:
            self.badReadCount = 0
            self.status = OximeterStatus.CONNECTED

            self.SPO2 = int(m.group('SPO2'))
            self.BPM = int(m.group('BPM'))
            self.readTime = dateutil.parser.parse(m.group('time'))

            self.alarmStateMachine.step(self.SPO2 <= self.config.spo2AlarmThreshold)
            self.alarm = int(m.group('alarm'), base=16) or self.alarmStateMachine.inSustainedMotion()

            self.motionDetected = (self.BPM >= self.config.awakeBpm)
            self.motionStateMachine.step(self.motionDetected)
            self.motionSustained = self.motionStateMachine.inSustainedMotion()

        else:
            self.badReadCount = min(self.badReadCount + 1, 4)
            if self.badReadCount == 3:
                self.reset(OximeterStatus.PROBE_DISCONNECTED, 'bad reads')

        RESET_TIME = 5
        if (self.resetTimer is not None) and self.resetTimer.active():
            self.resetTimer.reset(RESET_TIME)
        else:
            self.resetTimer = self.reactor.callLater(RESET_TIME, self.reset, OximeterStatus.CABLE_DISCONNECTED, 'timer')

    def connectionLost(self, reason):
        self.reset(OximeterStatus.CABLE_DISCONNECTED, 'connection lost')
        self.reader.searchForSerialPort()

class ForwardedAttrib(object):
    def __init__(self, propName):
        self.propName = propName

    def __get__(self, obj, objType):
        return getattr(obj.oximeterReader, self.propName)

class OximeterReader:
    def __init__(self, app):
        self.app = app
        self.reactor = app.reactor
        self.oximeterReader = OximeterReadProtocol(self)
        self.searchForSerialPort()

    def searchForSerialPort(self):
        self.loop = LoopingCall(self.connectToSerialPort)
        self.loop.start(2)

    def connectToSerialPort(self):
        devices = glob.glob('/dev/ttyUSB*')
        if len(devices) > 0:
            log('Started reading oximeter at %s' % devices[0])
            self.oximeterReader.reset(OximeterStatus.CABLE_DISCONNECTED, 'got connection')
            self.serialPort = SerialPort(self.oximeterReader, devices[0], self.reactor, timeout=3)
            self.loop.stop()

    def reset(self):
        self.oximeterReader.reset(OximeterStatus.CONNECTED, 'user reset')

    SPO2 = ForwardedAttrib('SPO2')
    BPM = ForwardedAttrib('BPM')
    alarm = ForwardedAttrib('alarm')
    readTime = ForwardedAttrib('readTime')
    motionDetected = ForwardedAttrib('motionDetected')
    motionSustained = ForwardedAttrib('motionSustained')
    status = ForwardedAttrib('status')

if __name__ == "__main__":
    from twisted.internet import reactor
    from Config import Config

    class MockApp:
        def __init__(self):
            self.reactor = reactor
            self.config = Config()

    setupLogging()
    reader = OximeterReader(MockApp())
    reactor.run()
