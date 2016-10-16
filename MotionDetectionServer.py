from twisted.internet import reactor, protocol

import io
import sys

import Image
import ImageOps
import ImageFilter
import ImageChops

from MotionStateMachine import MotionStateMachine

class JpegStreamReaderForMotion(protocol.Protocol):
    DETECTION_THRESHOLD = 0.01

    def __init__(self):
        self.data = ''
        self.motionDetected = False
        self.motionSustained = False
        self.prevImage = None
        self.motionStateMachine = MotionStateMachine()

        self.fp = open('/tmp/motion.log', 'w')

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
        self.motionStateMachine.step(motionDetected)
        motionSustained = self.motionStateMachine.inSustainedMotion()

        print '%d %d' % (motionDetected, motionSustained)
        sys.stdout.flush()

        self.prevImage = im

    def processChunk(self, data):
        if not data:
            return

        idx = data.find('\r\n')
        idx = data.find('\r\n\r\n', idx + 2)
        data = data[idx+4:]
        stream = io.BytesIO(data)
        img = Image.open(stream)
        self.processImage(img)

    def dataReceived(self, data):
        self.data += data
        chunks = self.data.split('--spionisto\r\n')

        for chunk in chunks[:-1]:
            self.processChunk(chunk)

        self.data = chunks[-1]

def startServer():
    print 'Starting...'
    reactor.listenTCP(9998, protocol.Factory.forProtocol(JpegStreamReaderForMotion))
    reactor.run()

if __name__ == "__main__":
    startServer()

