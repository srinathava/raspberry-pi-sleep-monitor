#!/usr/bin/env python

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
import json
import dateutil.parser
import subprocess

import Image
import ImageOps
import ImageFilter
import ImageChops

from MotionStateMachine import MotionStateMachine
from ProcessProtocolUtils import TerminalEchoProcessProtocol, \
        spawnNonDaemonProcess

import logging

from Config import Config

def log(msg):
    tnow = datetime.now()
    logging.info('%s: %s' % (tnow.isoformat(), msg))

def setupLogging():
    logFormatter = logging.Formatter("%(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    # tnow = datetime.now()
    # fileName = tnow.strftime('/home/pi/sleep-monitor-%Y-%m-%d-%H-%M-%S.log')
    # fileHandler = logging.FileHandler(fileName)
    # fileHandler.setFormatter(logFormatter)
    # rootLogger.addHandler(fileHandler)

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
        self.queues.append([q, request])
        while True:
            yield q.get()

    def _responseFailed(self, err, request):
        log('connection to client lost')

    def render_GET(self, request):
        log('getting new client of image stream')
        request.setHeader("content-type", 'multipart/x-mixed-replace; boundary=--spionisto')

        request.notifyFinish().addErrback(self._responseFailed, request)
        self.deferredRenderer(request)
        return server.NOT_DONE_YET

class JpegStreamReader(protocol.Protocol):
    def __init__(self):
        self.tnow = None

    def connectionMade(self):
        log('MJPEG Image stream received')
        self.tnow = datetime.now()
        self.cumData = 0
        self.cumCalls = 0

    def dataReceived(self, data):
        self.cumData += len(data)
        self.cumCalls += 1
        for (q, req) in self.factory.queues:
            req.write(data)
            q.put('')

        if datetime.now() - self.tnow > timedelta(seconds=1):
            log('Wrote %d bytes in the last second (%d cals)' % (self.cumData, self.cumCalls))
            self.tnow = datetime.now()
            self.cumData = 0
            self.cumCalls = 0

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

    def reset(self):
        self.transport.write('reset\n')

class OximeterReadProtocol(LineReceiver):
    PAT_LINE = re.compile(r'(?P<time>\d\d/\d\d/\d\d \d\d:\d\d:\d\d).*SPO2=(?P<SPO2>\d+).*BPM=(?P<BPM>\d+).*ALARM=(?P<alarm>\S+).*')

    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.reset()

    def reset(self):
        self.SPO2 = -1
        self.BPM = -1
        self.alarm = 0
        self.readTime = datetime.min
        self.motionDetected = False
        self.motionSustained = False
        self.setLineMode()

        self.alarmStateMachine = MotionStateMachine()
        self.alarmStateMachine.CALM_TIME = 0
        self.alarmStateMachine.SUSTAINED_TIME = self.config.spo2AlarmTime

        self.motionStateMachine = MotionStateMachine()
        self.motionStateMachine.CALM_TIME = self.config.sustainedTime
        self.motionStateMachine.SUSTAINED_TIME  = self.config.calmTime

        self.resetTimer = None

    def lineReceived(self, line):
        m = self.PAT_LINE.match(line)
        if m:
            self.SPO2 = int(m.group('SPO2'))
            self.BPM = int(m.group('BPM'))
            self.readTime = dateutil.parser.parse(m.group('time'))

            self.alarmStateMachine.step(self.SPO2 <= self.config.spo2AlarmThreshold)
            self.alarm = int(m.group('alarm'), base=16) or self.alarmStateMachine.inSustainedMotion()

            self.motionDetected = (self.BPM >= self.config.awakeBpm)
            self.motionStateMachine.step(self.motionDetected)
            self.motionSustained = self.motionStateMachine.inSustainedMotion()

            RESET_TIME = 5
            if self.resetTimer is None:
                self.resetTimer = reactor.callLater(RESET_TIME, self.reset)
            elif self.resetTimer.active():
                self.resetTimer.reset(RESET_TIME)
                
class StatusResource(resource.Resource):
    def __init__(self, app):
        self.app = app
        self.motionDetectorStatusReader = self.app.motionDetectorStatusReader
        self.oximeterReader = self.app.oximeterReader

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        status = {
                'SPO2': self.oximeterReader.SPO2,
                'BPM': self.oximeterReader.BPM,
                'alarm': bool(self.oximeterReader.alarm),
                'motion': int(self.motionDetectorStatusReader.motionSustained or self.oximeterReader.motionSustained),
                'readTime': self.oximeterReader.readTime.isoformat()
                }
        return json.dumps(status)

class PingResource(resource.Resource):
    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')
        request.setHeader("Access-Control-Allow-Origin", '*')

        status = { 'status': 'ready'}
        return json.dumps(status)

class GetConfigResource(resource.Resource):
    def __init__(self, app):
        self.app = app

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        status = {}
        for paramName in self.app.config.paramNames:
            status[paramName] = getattr(self.app.config, paramName)

        return json.dumps(status)

class UpdateConfigResource(resource.Resource):
    def __init__(self, app):
        self.app = app

    def render_GET(self, request):
        log('Got request to change parameters to %s' % request.args)

        for paramName in self.app.config.paramNames:
            # a bit of defensive coding. We really should not be getting
            # some random data here.
            if paramName in request.args:
                paramVal = int(request.args[paramName][0])
                log('setting %s to %d' % (paramName, paramVal))
                setattr(self.app.config, paramName, paramVal)

        self.app.resetAfterConfigUpdate()

        request.setHeader("content-type", 'application/json')
        status = { 'status': 'done'}
        return json.dumps(status)

class Logger:
    def __init__(self, app):
        self.oximeterReader = app.oximeterReader
        self.motionDetectorStatusReader = app.motionDetectorStatusReader

        self.lastLogTime = datetime.min
        self.logFile = None

        reactor.addSystemEventTrigger('before', 'shutdown', self.closeLastLogFile)

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

        if not os.path.isdir('../sleep_logs'):
            os.mkdir('../sleep_logs')

        self.logFile = open('../sleep_logs/%s.log.inprogress' % tstr, 'w', bufsize)

    def printToFile(self, logStr):
        self.logFile.write(logStr + '\n')

def startAudio():
    spawnNonDaemonProcess(reactor, TerminalEchoProcessProtocol(), '/opt/janus/bin/janus', 
                          ['janus', '-F', '/opt/janus/etc/janus/'])
    log('Started Janus')

    def startGstreamerAudio():
        spawnNonDaemonProcess(reactor, TerminalEchoProcessProtocol(), '/bin/sh', 
                              ['sh', 'gstream_audio.sh'])
        log('Started gstreamer audio')

    reactor.callLater(2, startGstreamerAudio)

def audioAvailable():
    out = subprocess.check_output(['arecord', '-l'])
    return ('USB Audio' in out)

def startAudioIfAvailable():
    if audioAvailable():
        startAudio()
    else:
        log('Audio not detected. Starting in silent mode')

class SleepMonitorApp:
    def __init__(self):
        queues = []

        self.config = Config()

        self.oximeterReader = OximeterReadProtocol(self)
        try:
            devices = glob.glob('/dev/ttyUSB*')
            SerialPort(oximeterReader, devices[0], reactor, timeout=3)
            log('Started reading oximeter at %s' % devices[0])
        except:
            pass

        self.motionDetectorStatusReader = MotionDetectionStatusReaderProtocol()
        spawnNonDaemonProcess(reactor, self.motionDetectorStatusReader, 'python', 
                ['python', 'MotionDetectionServer.py'])
        log('Started motion detection process')

        logger = Logger(self)
        logger.run()
        log('Started logging')

        factory = protocol.Factory()
        factory.protocol = JpegStreamReader
        factory.queues = queues
        reactor.listenTCP(9999, factory)
        log('Started listening for MJPEG stream')

        root = File('web')
        root.putChild('stream.mjpeg', MJpegResource(queues))
        root.putChild('status', StatusResource(self))
        root.putChild('ping', PingResource())
        root.putChild('getConfig', GetConfigResource(self))
        root.putChild('updateConfig', UpdateConfigResource(self))

        site = server.Site(root)
        PORT = 80
        reactor.listenTCP(PORT, site)
        log('Started webserver at port %d' % PORT)

        def startGstreamerVideo():
            spawnNonDaemonProcess(reactor, TerminalEchoProcessProtocol(), '/bin/sh', 
                                  ['sh', 'gstream_video.sh'])
            log('Started gstreamer video')

        # Wait 2 seconds for the ports to be ready to be sent to
        reactor.callLater(2, startGstreamerVideo)

        startAudioIfAvailable()

        reactor.run()

    def resetAfterConfigUpdate(self):
        log('Updated config')
        self.config.write()
        self.oximeterReader.reset()
        self.motionDetectorStatusReader.reset()

if __name__ == "__main__":
    setupLogging()
    log('Starting main method of sleep monitor')
    try:
        app = SleepMonitorApp()
    except:
        logging.exception("main() threw exception")
