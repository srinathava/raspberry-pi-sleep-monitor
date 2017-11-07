from twisted.internet import protocol
import sys
import os

class TerminalEchoProcessProtocol(protocol.ProcessProtocol):
    def __init__(self):
        self.outdata = ''
        self.errdata = ''

    def outLineReceived(self, line):
        print line
        sys.stdout.flush()

    def errLineReceived(self, line):
        print>>sys.stderr, line

    def outReceived(self, data):
        self.outdata += data
        lines = self.outdata.split('\n')
        for line in lines[:-1]:
            self.outLineReceived(line)

        self.outdata = lines[-1]

    def errReceived(self, data):
        self.errdata += data
        lines = self.errdata.split('\n')
        for line in lines[:-1]:
            self.errLineReceived(line)

        self.errdata = lines[-1]

    def dataReceived(self, data):
        self.outReceived(data)

def spawnNonDaemonProcess(reactor, protocol, executable, args):
    proc = reactor.spawnProcess(protocol, executable, args, os.environ)
    reactor.addSystemEventTrigger('before', 'shutdown', lambda: proc.signalProcess('TERM'))

if __name__ == "__main__":
    from twisted.internet import reactor
    proc = reactor.spawnProcess(TerminalEchoProcessProtocol(), 'nc', ['nc', '-l', '1234'])
    reactor.run()
