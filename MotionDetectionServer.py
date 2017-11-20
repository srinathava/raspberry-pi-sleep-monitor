from __future__ import print_function
from __future__ import division

from twisted.internet import reactor, protocol, stdio
from twisted.protocols import basic

import io
import sys

from PIL import Image
from PIL import ImageOps
from PIL import ImageFilter
from PIL import ImageChops
from Config import Config

from MotionStateMachine import MotionStateMachine

from datetime import datetime
import logging
import os

def log(msg):
    tnow = datetime.now()
    logging.info('%s: %s' % (tnow.isoformat(), msg))

def setupLogging():
    logFormatter = logging.Formatter("%(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

class ProcessInput(basic.LineReceiver):
    # This seemingly unused line is necessary to over-ride the delimiter
    # property of basic.LineReceiver which by default is '\r\n'. Do not
    # remove this!
    delimiter = os.linesep.encode('ASCII')

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
        self.data = b''
        self.motionDetected = False
        self.motionSustained = False
        self.prevImage = None
        self.imgcounter = 0
        self.saveImages = False

    def processImage(self, im):
        im = im.resize((320, 240))
        im = ImageOps.grayscale(im)
        im = im.filter(ImageFilter.BLUR)

        self.saveImage(im, 'orig')

        if not self.prevImage:
            self.prevImage = im
            return

        imd = ImageChops.difference(im, self.prevImage)
        self.saveImage(imd, 'diff')

        def mappoint(pix):
            if pix > 20:
                return 255
            else:
                return 0
        imbw = imd.point(mappoint)
        self.saveImage(imd, 'bw')

        hist = imbw.histogram()
        percentWhitePix = hist[-1] / (hist[0] + hist[-1])
        motionDetected = (percentWhitePix > self.DETECTION_THRESHOLD)
        self.factory.motionStateMachine.step(motionDetected)
        motionSustained = self.factory.motionStateMachine.inSustainedMotion()

        print('%d %d' % (motionDetected, motionSustained))
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
        self.imgcounter += 1

    def dataReceived(self, data):
        self.data += data
        chunks = self.data.split(b'--spionisto\r\n')

        for chunk in chunks[:-1]:
            self.processChunk(chunk)

        self.data = chunks[-1]

    def saveImage(self, im, prefix):
        if self.saveImages:
            im.save('/tmp/%s_%02d.jpeg' % (prefix, self.imgcounter))

def startServer():
    print('Starting...')

    factory = JpegStreamReaderFactory()

    stdio.StandardIO(ProcessInput(factory))

    reactor.listenTCP(9998, factory)

    print('MOTION_DETECTOR_READY')
    log('printed ready signal')
    sys.stdout.flush()

    reactor.run()

if __name__ == "__main__":
    setupLogging()
    log('Starting main method of motion detection')
    try:
        startServer()
    except:  # noqa: E722 (OK to use bare except)
        logging.exception("startServer() threw exception")
