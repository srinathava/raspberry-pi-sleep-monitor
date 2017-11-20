from twisted.internet import reactor, protocol, task
import sys
import glob

MJPEG_SEP = b'--spionisto\r\n'

images = []
for idx in range(45):
    fname = 'frames/frame%02d.jpeg' % idx
    with open(fname, 'rb') as fp:
        images.append(fp.read())

class MockVideoStream(protocol.Protocol):
    def __init__(self):
        self.curIdx = 0
        self.sampleTime = 0

    def connectionMade(self):
        self.sampleTime = self.factory.sampleTime
        lc = task.LoopingCall(self.writeImage)
        lc.start(self.sampleTime)

    def writeImage(self):
        self.curIdx = (self.curIdx + 1) % len(images)

        im = images[self.curIdx]
        self.transport.write(MJPEG_SEP)
        self.transport.write(b'\r\n')
        self.transport.write(im)

factory1 = protocol.ClientFactory()
factory1.protocol = MockVideoStream
factory1.sampleTime = 0.06667

factory2 = protocol.ClientFactory()
factory2.protocol = MockVideoStream
factory2.sampleTime = 1

reactor.connectTCP("localhost", 9999, factory1)
reactor.connectTCP("localhost", 9998, factory2)
reactor.run()
