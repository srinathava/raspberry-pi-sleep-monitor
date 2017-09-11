from __future__ import division

from twisted.internet import reactor, protocol, stdio
from twisted.protocols import basic

import io
import sys

import Image
import ImageOps
import ImageFilter
import ImageChops
from Config import Config

from MotionStateMachine import MotionStateMachine

from datetime import datetime, timedelta
import logging

def log(msg):
    tnow = datetime.now()
    logging.info('%s: %s' % (tnow.isoformat(), msg))

def setupLogging():
    logFormatter = logging.Formatter("%(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    tnow = datetime.now()
    fileName = tnow.strftime('/home/pi/motion-dection-log-%Y-%m-%d-%H-%M-%S.log')
    fileHandler = logging.FileHandler(fileName)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

class ProcessInput(basic.LineReceiver):
    # This seemingly unused line is necessary to over-ride the delimiter
    # property of basic.LineReceiver which by default is '\r\n'. Do not
    # remove this!
    from os import linesep as delimiter

    def __init__(self, factory):
        self.factory = factory

    def lineReceived(self, line):
        log('line recd: %s' % line)
        if line == 'reset':
            log('resetting motion detection service')
            self.factory.reset()

class JpegStreamReaderFactory(protocol.Factory):
    def __init__(self):
        self.protocol = JpegStreamReaderForMotion
        self.reset()

    def reset(self):
        self.config = Config()

        self.motionStateMachine = MotionStateMachine()
        log('starting motion state machine with (%d, %d)' % (self.config.sustainedTime, self.config.calmTime))
        self.motionStateMachine.SUSTAINED_TIME = self.config.sustainedTime
        self.motionStateMachine.CALM_TIME = self.config.calmTime

class JpegStreamReaderForMotion(protocol.Protocol):
    DETECTION_THRESHOLD = 0.01

    def __init__(self):
        self.data = ''
        self.motionDetected = False
        self.motionSustained = False
        self.prevImage = None
        self.imgcounter = 0

    def processImage(self, im):
        im = im.resize((320, 240))
        im = ImageOps.grayscale(im)
        im = im.filter(ImageFilter.BLUR)

        if not self.prevImage:
            self.prevImage = im
            return

        imd = ImageChops.difference(im, self.prevImage)

        def mappoint(pix):
            if pix > 20:
                return 255
            else:
                return 0
        imbw = imd.point(mappoint)

        hist = imbw.histogram()
        percentWhitePix = hist[-1]/(hist[0] + hist[-1])
        motionDetected = (percentWhitePix > self.DETECTION_THRESHOLD)
        self.factory.motionStateMachine.step(motionDetected)
        motionSustained = self.factory.motionStateMachine.inSustainedMotion()

        print '%d %d' % (motionDetected, motionSustained)
        sys.stdout.flush()

        self.prevImage = im

    def processChunk(self, data):
        if not data:
            return

        idx = data.find(b'\xff\xd8\xff')
        data = data[idx:]

        stream = io.BytesIO(data)
        img = Image.open(stream)
        self.processImage(img)
        self.imgcounter += 1;

    def dataReceived(self, data):
        self.data += data
        chunks = self.data.split('--spionisto\r\n')

        for chunk in chunks[:-1]:
            self.processChunk(chunk)

        self.data = chunks[-1]

def startServer():
    print 'Starting...'

    factory = JpegStreamReaderFactory()

    stdio.StandardIO(ProcessInput(factory))

    reactor.listenTCP(9998, factory)

    print 'MOTION_DETECTOR_READY'
    log('printed ready signal')
    sys.stdout.flush()

    reactor.run()

if __name__ == "__main__":
    setupLogging()
    log('Starting main method of motion detection')
    try:
        startServer()
    except:
        logging.exception("startServer() threw exception")

