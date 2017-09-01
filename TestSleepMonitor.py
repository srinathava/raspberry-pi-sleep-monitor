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

class ProcessInput(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, statusResource):
        self.statusResource = statusResource
        self.propMap = {'a': 'alarm', 'b': 'BPM', 'o': 'SPO2', 'm': 'motion'}

    def connectionMade(self):
        self.transport.write('Key: SPO2: o, BPM: b, motion: m, alarm: a\n')
        self.transport.write('>>> ')

    def lineReceived(self, line):
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

    def render_GET(self, request):
        request.setHeader("content-type", 'application/json')

        status = {
                'SPO2': self.SPO2,
                'BPM': self.BPM,
                'alarm': bool(self.alarm),
                'motion': int(self.motion),
                'readTime': datetime.now().isoformat()
                }
        return json.dumps(status)

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
    PORT = 8080
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
