from twisted.internet import reactor, protocol, defer
from twisted.web import server, resource
from twisted.web.static import File
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver

import io
import re
from datetime import datetime, timedelta
import glob
import os

import Image
import ImageOps
import ImageFilter
import ImageChops

from MotionStateMachine import MotionStateMachine

import logging

def log(msg):
    tnow = datetime.now()
    logging.info('%s: %s' % (tnow.isoformat(), msg))

def setupLogging():
    logFormatter = logging.Formatter("%(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    fileName = datetime.now().strftime('/tmp/sleep_monitor.log')
    fileHandler = logging.FileHandler(fileName)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

def async_sleep(seconds):
     d = defer.Deferred()
     reactor.callLater(seconds, d.callback, seconds)
     return d

class MJpegResource(resource.Resource):
    def __init__(self, queues):
        self.queues = queues

    @defer.inlineCallbacks
    def deferredRenderer(self, request):
        q = defer.DeferredQueue()
        self.queues.append(q)
        while True:
            data = yield q.get()
            request.write(data)

    def render_GET(self, request):
        request.setHeader("content-type", 'multipart/x-mixed-replace; boundary=--spionisto')
        self.deferredRenderer(request)
        return server.NOT_DONE_YET

class JpegStreamReader(protocol.Protocol):
    def connectionMade(self):
        log('MJPEG Image stream received')

    def dataReceived(self, data):
        for queue in self.factory.queues:
            queue.put(data)

class MotionDetectionStatusReaderProtocol(protocol.ProcessProtocol):
    PAT_STATUS = re.compile(r'(\d) (\d)')
    def __init__(self):
        self.data = ''
        self.motionDetected = False
        self.motionSustained = False

    def outReceived(self, data):
        self.data += data
        lines = self.data.split('\n')
        if len(lines) > 1:
            line = lines[-2]
            if self.PAT_STATUS.match(line):
                (self.motionDetected, self.motionSustained) = [int(word) for word in line.split()]

        self.data = lines[-1]

class OximeterReadProtocol(LineReceiver):
    PAT_LINE = re.compile(r'(?P<time>\d\d/\d\d/\d\d \d\d:\d\d:\d\d).*SPO2=(?P<SPO2>\d+).*BPM=(?P<BPM>\d+).*ALARM=(?P<alarm>\S+).*')

    def __init__(self):
        self.SPO2 = -1
        self.BPM = -1
        self.alarm = -1
        self.readTime = datetime.min
        self.motionDetected = False
        self.motionSustained = False
        self.setLineMode()

        self.alarmStateMachine = MotionStateMachine()
        self.alarmStateMachine.CALM_TIME = 0
        self.alarmStateMachine.SUSTAINED_TIME = 20

        self.motionStateMachine = MotionStateMachine()
        self.motionStateMachine.CALM_TIME = 100
        self.motionStateMachine.SUSTAINED_TIME  = 10

    def lineReceived(self, line):
        m = self.PAT_LINE.match(line)
        if m:
            self.SPO2 = int(m.group('SPO2'))
            self.BPM = int(m.group('BPM'))
            self.readTime = dateutil.parser.parse(m.group('time'))

            self.alarmStateMachine.step(self.SPO2 <= 94)
            self.alarm = int(m.group('alarm'), base=16) or self.alarmStateMachine.inSustainedMotion()

            self.motionDetected = (self.BPM >= 140)
            self.motionStateMachine.step(self.motionDetected)
            self.motionSustained = self.motionStateMachine.inSustainedMotion()

class StatusResource(resource.Resource):
    def __init__(self, motionDetectorStatusReader, oximeterReader):
        self.motionDetectorStatusReader = motionDetectorStatusReader
        self.oximeterReader = oximeterReader

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        status = {
                'SPO2': self.oximeterReader.SPO2,
                'BPM': self.oximeterReader.BPM,
                'alarm': bool(self.oximeter.alarm),
                'motion': int(self.motionDetectorStatusReader.motionSustained or self.oximeterReader.motionSustained),
                'readTime': self.oximeter.readTime.isoformat()
                }
        return json.dumps(status)

class Logger:
    def __init__(self, oximeterReader, motionDetectorStatusReader):
        self.oximeterReader = oximeterReader
        self.motionDetectorStatusReader = motionDetectorStatusReader

        self.lastLogTime = datetime.min
        self.logFile = None

    @defer.inlineCallbacks
    def run(self):
        while True:
            yield async_sleep(1)

            tnow = datetime.now()
            if self.oximeterReader.SPO2 != -1:
                tstr = tnow.strftime('%Y-%m-%d-%H-%M-%S')
                spo2 = self.oximeterReader.SPO2
                bpm = self.oximeterReader.BPM
                alarm = self.oximeterReader.alarm
                motionDetected = self.motionDetectorStatusReader.motionDetected
                motionSustained = self.motionDetectorStatusReader.motionSustained

                logStr = '%(spo2)d %(bpm)d %(alarm)d %(motionDetected)d %(motionSustained)d' % locals()

                log('STATUS: %s' % logStr)

                if self.logFile is None:
                    self.createNewLogFile(tstr)

                self.printToFile('%(tstr)s %(logStr)s' % locals())
                self.lastLogTime = tnow
            else:
                if tnow - self.lastLogTime > timedelta(hours=2):
                    self.closeLastLogFile()

    def closeLastLogFile(self):
        if self.logFile is not None:
            self.logFile.close()
            newname = self.logFile.name.replace('.inprogress', '')
            os.rename(self.logFile.name, newname)
            self.logFile = None

    def createNewLogFile(self, tstr):
        bufsize = 1 # line buffering
        self.logFile = open('../sleep_logs/%s.log.inprogress' % tstr, 'w', bufsize)

    def printToFile(self, logStr):
        self.logFile.write(logStr + '\n')

def main():
    queues = []

    oximeterReader = OximeterReadProtocol()
    try:
        devices = glob.glob('/dev/ttyUSB*')
        SerialPort(oximeterReader, devices[0], reactor, timeout=3)
        log('Started reading oximeter at %s' % devices[0])
    except:
        pass

    motionDetectorStatusReader = MotionDetectionStatusReaderProtocol()
    reactor.spawnProcess(motionDetectorStatusReader, 'python', 
            ['python', 'MotionDetectionServer.py'])
    log('Started motion deteciton process')

    logger = Logger(oximeterReader, motionDetectorStatusReader)
    logger.run()
    log('Started logging')

    factory = protocol.Factory()
    factory.protocol = JpegStreamReader
    factory.queues = queues
    reactor.listenTCP(9999, factory)
    log('Started listening for MJPEG stream')

    root = File('.')
    root.putChild('stream.mjpeg', MJpegResource(queues))
    root.putChild('status', StatusResource(motionDetectorStatusReader, oximeterReader))

    site = server.Site(root)
    reactor.listenTCP(8080, site)
    log('Started webserver at port 8080')

    reactor.run()

if __name__ == "__main__":
    setupLogging()
    log('Starting main method of sleep monitor')
    try:
        main()
    except:
        logging.exception("main() threw exception")
