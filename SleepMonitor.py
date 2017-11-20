#!/usr/bin/env python

from __future__ import print_function

from twisted.internet import reactor, protocol, defer, interfaces
import twisted.internet.error
from twisted.web import server, resource
from twisted.web.static import File
from zope.interface import implementer

import re
from datetime import datetime, timedelta
import os
import json
import subprocess
import sys

from ProcessProtocolUtils import spawnNonDaemonProcess, TerminalEchoProcessProtocol
from OximeterReader import OximeterReader
from ZeroConfUtils import startZeroConfServer

from LoggingUtils import log, setupLogging, LoggingProtocol

from Config import Config
from Constants import MotionReason

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def async_sleep(seconds):
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, seconds)
    return d

def check_output(args):
    return subprocess.check_output(args, universal_newlines=True)

class MJpegResource(resource.Resource):
    def __init__(self, queues):
        self.queues = queues

    def setupProducer(self, request):
        producer = JpegProducer(request)
        request.notifyFinish().addErrback(self._responseFailed, producer)
        request.registerProducer(producer, True)

        self.queues.append(producer)

    def _responseFailed(self, err, producer):
        log('connection to client lost')
        producer.stopProducing()

    def render_GET(self, request):
        log('getting new client of image stream')
        request.setHeader("content-type", 'multipart/x-mixed-replace; boundary=--spionisto')

        self.setupProducer(request)
        return server.NOT_DONE_YET

class LatestImageResource(resource.Resource):
    def __init__(self, factory):
        self.factory = factory

    def render_GET(self, request):
        request.setHeader("content-type", 'image/jpeg')
        return self.factory.latestImage

@implementer(interfaces.IPushProducer)
class JpegProducer(object):
    def __init__(self, request):
        self.request = request
        self.isPaused = False
        self.isStopped = False
        self.delayedCall = None

    def cancelCall(self):
        if self.delayedCall:
            self.delayedCall.cancel()
            self.delayedCall = None

    def pauseProducing(self):
        self.isPaused = True
        self.cancelCall()
        # log('producer is requesting to be paused')

    def resetPausedFlag(self):
        self.isPaused = False
        self.delayedCall = None

    def resumeProducing(self):
        # calling self.cancelCall is defensive. We should not really get
        # called with multiple resumeProducing calls without any
        # pauseProducing in the middle.
        self.cancelCall()
        self.delayedCall = reactor.callLater(1, self.resetPausedFlag)
        # log('producer is requesting to be resumed')

    def stopProducing(self):
        self.isPaused = True
        self.isStopped = True
        log('producer is requesting to be stopped')

MJPEG_SEP = b'--spionisto\r\n'

class JpegStreamReader(protocol.Protocol):
    def __init__(self):
        self.tnow = None

    def connectionMade(self):
        log('MJPEG Image stream received')
        self.data = b''
        self.tnow = datetime.now()
        self.cumDataLen = 0
        self.cumCalls = 0

    def dataReceived(self, data):
        self.data += data

        chunks = self.data.rsplit(MJPEG_SEP, 1)

        dataToSend = ''
        if len(chunks) == 2:
            subchunks = chunks[0].rsplit(MJPEG_SEP, 1)

            lastchunk = subchunks[-1]
            idx = lastchunk.find(b'\xff\xd8\xff')
            self.factory.latestImage = lastchunk[idx:]

            dataToSend = chunks[0] + MJPEG_SEP

        self.data = chunks[-1]

        self.cumDataLen += len(dataToSend)
        self.cumCalls += 1

        for producer in self.factory.queues:
            if (not producer.isPaused):
                producer.request.write(dataToSend)

        if datetime.now() - self.tnow > timedelta(seconds=1):
            # log('Wrote %d bytes in the last second (%d cals)' % (self.cumDataLen, self.cumCalls))
            self.tnow = datetime.now()
            self.cumDataLen = 0
            self.cumCalls = 0

class MotionDetectionStatusReaderProtocol(TerminalEchoProcessProtocol):
    PAT_STATUS = re.compile(r'(\d) (\d)')

    def __init__(self, app):
        TerminalEchoProcessProtocol.__init__(self)
        self.motionDetected = False
        self.motionSustained = False
        self.app = app

    def outLineReceived(self, line):
        if line.startswith('MOTION_DETECTOR_READY'):
            self.app.startGstreamerVideo()

        if self.PAT_STATUS.match(line):
            (self.motionDetected, self.motionSustained) = [int(word) for word in line.split()]
        else:
            log('MotionDetector: %s' % line)

    def errLineReceived(self, line):
        log('MotionDetector: error: %s' % line)

    def reset(self):
        self.transport.write(b'reset\n')

class StatusResource(resource.Resource):
    def __init__(self, app):
        self.app = app
        self.motionDetectorStatusReader = self.app.motionDetectorStatusReader
        self.oximeterReader = self.app.oximeterReader

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        motion = 0
        motionReason = MotionReason.NONE
        if self.motionDetectorStatusReader.motionSustained:
            motion = 1
            motionReason = MotionReason.CAMERA
        elif self.oximeterReader.motionSustained:
            motion = 1
            motionReason = MotionReason.BPM

        status = {
            'SPO2': self.oximeterReader.SPO2,
            'BPM': self.oximeterReader.BPM,
            'alarm': bool(self.oximeterReader.alarm),
            'motion': motion,
            'motionReason': motionReason,
            'readTime': self.oximeterReader.readTime.isoformat(),
            'oximeterStatus': self.oximeterReader.status
        }
        return json.dumps(status).encode()

class PingResource(resource.Resource):
    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')
        request.setHeader("Access-Control-Allow-Origin", '*')

        status = {'status': 'ready'}
        return json.dumps(status).encode()

class GetConfigResource(resource.Resource):
    def __init__(self, app):
        self.app = app

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        status = {}
        for paramName in self.app.config.paramNames:
            status[paramName] = getattr(self.app.config, paramName)

        return json.dumps(status).encode()

class UpdateConfigResource(resource.Resource):
    def __init__(self, app):
        self.app = app

    def render_GET(self, request):
        log('Got request to change parameters to %s' % request.args)

        args = {k.decode('utf-8'): int(v[0]) for k, v in request.args.items()}

        for paramName in self.app.config.paramNames:
            # a bit of defensive coding. We really should not be getting
            # some random data here.
            if paramName in args:
                paramVal = args[paramName]
                log('setting %s to %d' % (paramName, paramVal))
                setattr(self.app.config, paramName, paramVal)

        self.app.resetAfterConfigUpdate()

        request.setHeader("content-type", 'application/json')
        status = {'status': 'done'}
        return json.dumps(status).encode()

class InfluxLoggerClient(LoggingProtocol):
    def __init__(self):
        LoggingProtocol.__init__(self, 'InfluxLogger')

    def log(self, spo2, bpm, motion, alarm):
        self.transport.write(b'%d %d %d %d\n' % (spo2, bpm, motion, alarm))

class Logger:
    def __init__(self, app):
        self.oximeterReader = app.oximeterReader
        self.influxLogger = app.influxLogger
        self.motionDetectorStatusReader = app.motionDetectorStatusReader

        self.lastLogTime = datetime.min
        self.logFile = None

        reactor.addSystemEventTrigger('before', 'shutdown', self.closeLastLogFile)

    @defer.inlineCallbacks
    def run(self):
        while True:
            yield async_sleep(2)

            spo2 = self.oximeterReader.SPO2
            bpm = self.oximeterReader.BPM
            alarm = self.oximeterReader.alarm
            motionDetected = self.motionDetectorStatusReader.motionDetected

            self.influxLogger.log(spo2, bpm, motionDetected, alarm)

            tnow = datetime.now()
            if self.oximeterReader.SPO2 != -1:
                tstr = tnow.strftime('%Y-%m-%d-%H-%M-%S')
                motionSustained = self.motionDetectorStatusReader.motionSustained

                logStr = '%(spo2)d %(bpm)d %(alarm)d %(motionDetected)d %(motionSustained)d' % locals()

                # Do not use log here to avoid overloading the log file
                # with stats.
                print('STATUS: %s' % logStr)

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
        bufsize = 1  # line buffering

        sleep_logs_dir = os.path.join(SCRIPT_DIR, '..', 'sleep_logs')
        if not os.path.isdir(sleep_logs_dir):
            os.mkdir(sleep_logs_dir)

        logFileName = '%s.log.inprogress' % tstr
        self.logFile = open(os.path.join(sleep_logs_dir, logFileName), 'w', bufsize)

    def printToFile(self, logStr):
        self.logFile.write(logStr + '\n')

def startAudio():
    spawnNonDaemonProcess(reactor, LoggingProtocol('janus'), '/opt/janus/bin/janus',
                          ['janus', '-F', '/opt/janus/etc/janus/'])
    log('Started Janus')

    def startGstreamerAudio():
        spawnNonDaemonProcess(reactor, LoggingProtocol('gstream-audio'), '/bin/sh',
                              ['sh', 'gstream_audio.sh'])
        log('Started gstreamer audio')

    reactor.callLater(2, startGstreamerAudio)

def audioAvailable():
    out = check_output(['arecord', '-l'])
    return ('USB Audio' in out)

def startAudioIfAvailable():
    if audioAvailable():
        startAudio()
    else:
        log('Audio not detected. Starting in silent mode')

class SleepMonitorApp:
    def startGstreamerVideo(self):

        videosrc = '/dev/video0'

        try:
            out = check_output(['v4l2-ctl', '--list-devices'])
        except subprocess.CalledProcessError as e:
            out = e.output

        lines = out.splitlines()
        for (idx, line) in enumerate(lines):
            if 'bcm2835' in line:
                nextline = lines[idx + 1]
                videosrc = nextline.strip()

        spawnNonDaemonProcess(reactor, LoggingProtocol('gstream-video'), '/bin/sh',
                              ['sh', 'gstream_video.sh', videosrc])

        log('Started gstreamer video using device %s' % videosrc)

    def __init__(self):
        queues = []

        self.config = Config()
        self.reactor = reactor

        self.oximeterReader = OximeterReader(self)

        self.motionDetectorStatusReader = MotionDetectionStatusReaderProtocol(self)
        spawnNonDaemonProcess(reactor, self.motionDetectorStatusReader, 'python',
                              ['python', os.path.join(SCRIPT_DIR, 'MotionDetectionServer.py')])
        log('Started motion detection process')

        self.influxLogger = InfluxLoggerClient()
        spawnNonDaemonProcess(reactor, self.influxLogger, 'python',
                              ['python', os.path.join(SCRIPT_DIR, 'InfluxDbLogger.py')])
        log('Started influxdb logging process')

        logger = Logger(self)
        logger.run()
        log('Started logging')

        factory = protocol.Factory()
        factory.protocol = JpegStreamReader
        factory.queues = queues
        factory.latestImage = None
        reactor.listenTCP(9999, factory)
        log('Started listening for MJPEG stream')

        root = File(os.path.join(SCRIPT_DIR, 'web'))
        root.putChild(b'stream.mjpeg', MJpegResource(queues))
        root.putChild(b'latest.jpeg', LatestImageResource(factory))
        root.putChild(b'status', StatusResource(self))
        root.putChild(b'ping', PingResource())
        root.putChild(b'getConfig', GetConfigResource(self))
        root.putChild(b'updateConfig', UpdateConfigResource(self))

        site = server.Site(root)
        PORT = 80
        BACKUP_PORT = 8080

        portUsed = PORT
        try:
            reactor.listenTCP(PORT, site)
            log('Started webserver at port %d' % PORT)
        except twisted.internet.error.CannotListenError:
            portUsed = BACKUP_PORT
            reactor.listenTCP(BACKUP_PORT, site)
            log('Started webserver at port %d' % BACKUP_PORT)

        if portUsed == 80:
            startZeroConfServer(portUsed)

        startAudioIfAvailable()

        reactor.run()

    def resetAfterConfigUpdate(self):
        self.config.write()
        log('Updated config')
        self.oximeterReader.reset()
        self.motionDetectorStatusReader.reset()

if __name__ == "__main__":
    import logging
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        from twisted import python
        python.log.startLogging(sys.stdout)

    setupLogging()
    log('Starting main method of sleep monitor')
    try:
        app = SleepMonitorApp()
    except:  # noqa: E722 (OK to use bare except)
        logging.exception("main() threw exception")
