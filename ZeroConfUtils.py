import socket

from zeroconf import ServiceInfo, Zeroconf
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
import logging

from LoggingUtils import log

class ZeroConfServer:
    def __init__(self, portNumber):
        self.portNumber = portNumber
        self.loop = LoopingCall(self.searchForIpAddress)
        self.loop.start(2)

    def registerService(self, ip):
        info = ServiceInfo("_http._tcp.local.",
                           "Raspberry Pi Sleep Monitor._http._tcp.local.",
                           socket.inet_aton(ip), self.portNumber, 0, 0,
                           {}, "sleepmonitor.local.")

        zeroconf = Zeroconf()
        log("Registering zeroconf service...")
        zeroconf.register_service(info)

        def unregisterService():
            log("Unregistering zeroconf service...")
            zeroconf.unregister_service(info)

        reactor.addSystemEventTrigger('before', 'shutdown', unregisterService)

    def searchForIpAddress(self):
        try:
            ip = _getip()
            self.registerService(ip)
            self.loop.stop()
        except:
            logging.exception("Error getting IP. Retrying after 2 seconds...")
            pass


def startZeroConfServer(portNumber):
    ZeroConfServer(portNumber)

def _getip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

if __name__ == "__main__":
    from twisted.internet import stdio
    from twisted.protocols import basic

    import logging
    logging.basicConfig(level=logging.INFO, format='%(relativeCreated)6d %(threadName)s %(message)s')

    class Echo(basic.LineReceiver):
        from os import linesep as delimiter

        def connectionMade(self):
            self.transport.write(b'Press <enter> to quit')

        def lineReceived(self, line):
            reactor.stop()

    stdio.StandardIO(Echo())
    startZeroConfServer()
    reactor.run()
