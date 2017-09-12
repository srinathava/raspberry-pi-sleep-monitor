#!/usr/bin/env python

from twisted.internet import reactor, stdio
from twisted.web import server, resource
from twisted.web.static import File
from twisted.protocols import basic

from datetime import datetime
import os
import logging
import json

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

from Constants import *

MOTION_REASON_MAP = {
        0: MotionReason.NONE, 
        1: MotionReason.CAMERA, 
        2: MotionReason.BPM
        }
OXIMETER_STATUS_MAP = {
        0: OximeterStatus.CONNECTED, 
        1: OximeterStatus.PROBE_DISCONNECTED, 
        2: OximeterStatus.CABLE_DISCONNECTED}

def mapToStr(m):
    return ', '.join(['%d(%s)' % (k, v) for (k, v) in m.iteritems()])

class ProcessInput(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, statusResource):
        self.statusResource = statusResource
        self.propMap = {'a': 'alarm', 'b': 'BPM', 'o': 'SPO2', 'm': 'motion', 'mr': 'motionReason', 'st': 'oximeterStatus'}

    def connectionMade(self):
        self.transport.write('Keys: \n')
        for (p, name) in self.propMap.iteritems():
            self.transport.write('%s : %s\n' % (p, name))

        self.transport.write('motionReason: %s\n' % mapToStr(MOTION_REASON_MAP))
        self.transport.write('oximeterStatus: %s\n' % mapToStr(OXIMETER_STATUS_MAP))

        self.transport.write('>>> ')

    def lineReceived(self, line):
        if line == 'print':
            for (p, name) in self.statusResource.getStatus().iteritems():
                print '%s: %s, ' % (p, name)

            print
        else:
            try:
                (propName, propValStr) = line.split('=')
                propVal = int(propValStr)
                realPropName = self.propMap[propName]
                setattr(self.statusResource, realPropName, propVal)
            except:
                self.transport.write('*** Error ***\n')

        self.transport.write('>>> ')

class StatusResource(resource.Resource):
    def __init__(self):
        self.SPO2 = 100
        self.BPM = 100
        self.alarm = 0
        self.motion = 0
        self.motionReason = 0
        self.oximeterStatus = 0

    def getStatus(self):
        return {
                'SPO2': self.SPO2,
                'BPM': self.BPM,
                'alarm': bool(self.alarm),
                'motion': int(self.motion),
                'readTime': datetime.now().isoformat(),
                'motionReason': MOTION_REASON_MAP[self.motionReason],
                'oximeterStatus': OXIMETER_STATUS_MAP[self.oximeterStatus]
                }

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')
        return json.dumps(self.getStatus())

class PingResource(resource.Resource):
    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')
        request.setHeader("Access-Control-Allow-Origin", '*')

        status = { 'status': 'ready'}
        return json.dumps(status)

def main():
    log('Current pwd = %s' % os.getcwd())

    statusResource = StatusResource()

    root = File('web')
    root.putChild('status', statusResource)
    root.putChild('ping', PingResource())

    stdio.StandardIO(ProcessInput(statusResource))
    site = server.Site(root)
    PORT = 80
    reactor.listenTCP(PORT, site)
    log('Started webserver at port %d' % PORT)

    reactor.run()

if __name__ == "__main__":
    setupLogging()
    log('Starting main method of sleep monitor')
    try:
        main()
    except:
        logging.exception("main() threw exception")
