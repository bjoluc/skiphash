import socket, sys, time, logging
from threading import Thread

CHARSET = "utf-8"

logger = logging.Logger("vaud.node")

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

"""
A class for storing a hostname and a port
"""
class Address:
    
    def __init__(self, host, port):
        self._host = host
        self._port = port
    
    @property
    def host(self):
        return self._host
    
    @property
    def port(self):
        return self._port
    
    def toTuple(self):
        return (self._host, self._port)
    
    def __str__(self):
        return "{s}:{d}".format(self._host, self._port)


class Node:

    """
    Initializes a new node running a thread listening for incoming messages on the port specified.
    """
    def __init__(self, port: int, timeoutInterval: int = None):
        self._address = Address(get_ip(), port)

        # create a UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(.1)

        # bind socket to port
        logger.info('Starting up node at %s', self._address)
        self._socket.bind(self._address.toTuple())
        # start listening
        self._listener = Node.Listener(self)
        self._listener.start()


        self._timer = None
        if timeoutInterval is not None:
            self._timer = Node.Timer(self, timeoutInterval)
            self._timer.start()
        
    class Listener(Thread):

        def __init__(self, node: "Node"):
            Thread.__init__(self)
            self._node = node
            self._listening = False

        def run(self):
            logger.debug('%s listening', self._node)
            self._listening = True
            while self._listening:
                try:
                    data, address = self._node._socket.recvfrom(4096)
                except socket.timeout:
                    continue
                
                if not data:
                    continue
                
                source = Address(*address)
                logger.debug('%s: Received %d bytes from Node at %d', self._node, len(data), source)
                self._node._inputHandler(data.decode(CHARSET))
            
            # close the socket
            self._node._socket.close()
        
        def shutdown(self):
            self._listening = False
            self.join()
    
    class Timer(Thread):

        def __init__(self, node: "Node", timeoutInterval: int):
            Thread.__init__(self)
            self._node = node
            self._timeoutInterval = timeoutInterval
            self._running = False
        
        def run(self):
            self._running = True
            while self._running:
                time.sleep(self._timeoutInterval)
                self._node._timeout()
        
        def shutdown(self):
            self._running = False
            self.join()
    
    """
    To be overridden by subclasses
    """
    def _inputHandler(self, data: str):
        raise NotImplementedError
    
    """
    To be overridden by subclasses
    """
    def _timeout(self):
        raise NotImplementedError
    
    def send(self, data: str, address: Address):
        self._socket.sendto(data.encode(CHARSET), address.toTuple())
    
    def shutdown(self):
        self._listener.shutdown()
        if self._timer is not None:
            self._timer.shutdown()

    @property
    def address(self):
        return self._address
    
    def __str__(self):
        return "Node at {}".format(self._address)
