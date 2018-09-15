import logging
import pickle
import socket
import time
from threading import Thread
from typing import List, Union

from twisted.application import internet
from twisted.internet import endpoints, protocol, reactor, defer
from twisted.internet.interfaces import IAddress
from twisted.internet.address import IPv4Address
from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint, connectProtocol
from twisted.protocols.basic import LineReceiver

logger = logging.getLogger(__name__)

"""
Returns the local machine's primary IP address.
"""
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class Node:
    
    def __init__(self, reactor, port: int, timeoutInterval: int = None):
        """
        Initializes a new node listening for incoming messages on the port specified.
        """
        logger.info("Initializing node on port %d", port)
        self.reactor = reactor
        self._address = IPv4Address('TCP', get_ip(), port)
        self._protocolFactory = self.ProtocolFactory(self)
        self._port = None
        self._startServer()

        self._timer = None
        if timeoutInterval is not None:
            self._timer = Node.Timer(self, timeoutInterval)
            self._timer.start()
    
    @defer.inlineCallbacks
    def _startServer(self):
        self._port = yield TCP4ServerEndpoint(self.reactor, self.port).listen(self._protocolFactory)
    
    class RemoteCallProtocol(LineReceiver):
        """
        A Twisted protocol implementation that serializes, transmits, deserializes and executes method calls
        """
        def __init__(self, node: "Node", factory, peerAddress: IAddress):
            self._node = node
            self.factory = factory
            self.peerAddress = peerAddress
            self.shutdownFinished = defer.Deferred()
        
        def connectionMade(self):
            logger.info("Connected to %s.", self.peerAddress)
            # check if there is a deferred for this instance that we have to trigger
            if self.peerAddress in self.factory.instances:
                instance = self.factory.instances[self.peerAddress]
                if isinstance(instance, defer.Deferred):
                    instance.callback(self)
            self.factory.instances[self.peerAddress] = self
        
        def connectionLost(self, reason):
            logger.info("Connection to %s lost.", self.peerAddress)
            self.factory.instances.pop(self.peerAddress)
            self.shutdownFinished.callback(True)
        
        def lineReceived(self, line: str):
            logger.debug("Received line: %s", line)
            #arg_list = pickle.load(line)
            # TODO Checking and making the call
            pass
        
        def sendCall(self, methodName: str, arguments: List = None):
            # pickle call and send it 
            toBePickled = [methodName]
            if arguments is not None:
                toBePickled.extend(arguments)
            self.sendLine(pickle.dump(toBePickled))
    
    class ProtocolFactory(protocol.ClientFactory):

        def __init__(self, node: "Node"):
            self.node = node
            self.instances = {}

        def buildProtocol(self, addr):
            # Overrides the protocol.Factory.buildProtocol method.
            #self.resetDelay()
            return Node.RemoteCallProtocol(self.node, self, addr)

        def getProtocol(self, peerAddress: IAddress) -> Union["Node.RemoteCallProtocol", defer.Deferred]:
            """
            Custom method for returning either a protocol instance or a deferred for a new protocol instance
            """
            if not peerAddress in self.instances:
                # there is no (maybe deferred) protocol instance for the peer
                # we have to establish a new connection in order to get a protocol instance
                self.instances[peerAddress] = defer.Deferred()
                logger.info("Establishing TCP connection to %s...", peerAddress)
                self.node.reactor.connectTCP(peerAddress.host, peerAddress.port, self)
            return self.instances[peerAddress]
        
        def shutdownProtocols(self) -> defer.Deferred:
            for protocol in self.instances.values():
                deferreds = []
                if not isinstance(protocol, defer.Deferred):
                    deferreds.append(protocol.shutdownFinished)
                    protocol.transport.loseConnection()
            return defer.gatherResults(deferreds)
        
        def clientConnectionFailed(self, connector, reason):
            logger.warn("Client connection failed")

    class Timer(Thread):

        def __init__(self, node: "Node", timeoutInterval: int):
            Thread.__init__(self)
            self._node = node
            self._timeoutInterval = timeoutInterval
            self._running = False
        
        def run(self):
            self._running = True
            while self._running:
                self._node._timeout()
                time.sleep(self._timeoutInterval)
        
        def shutdown(self):
            self._running = False
            self.join()
    
    """
    To be overridden by subclasses
    """
    def _timeout(self):
        pass
    
    @defer.inlineCallbacks
    def callRemoteMethod(self, remoteAddress: IAddress, methodName: str, arguments: List = None):
        protocol = yield self._protocolFactory.getProtocol(remoteAddress)

        protocol.sendCall(methodName, arguments)
    
    def shutdown(self):
        stoppedListening = defer.maybeDeferred(self._port.stopListening)
        shutdownProtocols = self._protocolFactory.shutdownProtocols()
        if self._timer is not None:
            self._timer.shutdown()
        return defer.gatherResults([stoppedListening, shutdownProtocols])
    
    @property
    def host(self):
        return self._address.host

    @property
    def port(self):
        return self._address.port
    
    @property
    def address(self):
        return self._address

    def __str__(self):
        return "Node at {}".format(self.address)

"""
A class representing a remote node.
Methods called on its instances will be executed on the
remote Node instance, providing the same parameters.
"""
class RemoteNode:
    
    def __init__(self, node: Node, address: IAddress):
        self._node = node
        self._address = address
    
    def __str__(self):
        return "Remote Node at {}".format(self._address)
