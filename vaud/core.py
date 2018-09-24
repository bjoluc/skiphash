import logging
import random
import sys
from functools import total_ordering
from ipaddress import IPv4Address
from typing import Any, Union

from bitarray import bitarray
from twisted.application.internet import TimerService
from twisted.internet import defer, error, reactor
from twisted.spread import flavors, pb

from cityhash import CityHash64
from vaud import thisHost

logger = logging.getLogger(__name__)

# For twisted reactor method calls:
# pylint: disable=maybe-no-member

def sleep(seconds: int):
    """Returns a deferred that fires after the time given has passed."""
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, None)
    return d

def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)

def linkedDeferred(d: Union[defer.Deferred, Any]):
    """
    When yielding the same deferred from multiple inlineCallbacks-decorated
    methods, only one of those methods will get the deferred's value.
    If you still want to receive the value you can use this function,
    providing your deferred (or value). It will return another deferred that will be
    called with the same value as the initial deferred (or just the input value).
    Each generator can thus yield another deferred (the results of this function's calls)
    while still getting the same value.
    I don't like that this cheat is needed in Twisted!
    """
    if isinstance(d, defer.Deferred):
        newDeferred = defer.Deferred()
        def callback(value):
            newDeferred.callback(value)
            return value
        def errback(value):
            newDeferred.errback(value)
            return value
        d.addCallbacks(callback, errback)
        return newDeferred
    return d

def projectOntoUnitInterval(input: int, inputBitLength: int) -> float:
    """
    Projects any integer consisting of inputBitLength bits onto the [0,1) interval.
    """
    return 2**(-inputBitLength) * input

def randomBitArray(byteSize):
    byteString = bytes(random.getrandbits(8) for _ in range(byteSize))
    bitArray = bitarray()
    bitArray.frombytes(byteString)
    return bitArray

class CopyableBitArray(bitarray, flavors.Copyable, flavors.RemoteCopy):
    """
    Like bitarray, but copyable by Twisted's Perspective Broker.
    Note: Do only use multiples of 8 as the BitArray length, as copying
    will transfer the BitArray into bytes and backwards.
    """

    def getStateToCopy(self):
        return self.tobytes()
        
    def setCopyableState(self, state):
        self.frombytes(state)
    
    def unitValue(self):
        """
        Returns the corresponding value in the [0,1) interval.
        """
        return projectOntoUnitInterval(int(self), self.length())

pb.setUnjellyableForClass('vaud.core.CopyableBitArray', CopyableBitArray)

@total_ordering
class NodeReference(flavors.Copyable, flavors.RemoteCopy):
    """
    A NodeReference stores a host (IPv4Address, provided as string)
    and a port (int) of a distant node
    and will on demand connect to that node.
    Also, remote node methods can be invoked directly on a NodeReference
    and will be executed by the referenced node, returning a (maybe) deferred for
    the remote method's result.
    Each NodeReference object has a unique uniformly random
    64 bit id which is a hash of its host and port.
    Comparing NodeReference objects will compare their ids.
    """

    _remoteReferenceDict = {}
    """A dictionary for storing existing RemoteReference instances, indexed by their host and port"""

    def __init__(self, host: str = None, port: int = None):
        if host is not None:
            self._host = IPv4Address(host)
        self._port = port
        self.postInit()
        # CAUTION: For some reasons, this is not called when
        # the object is copied by the perspective broker.
        # Use postInit() instead.
    
    def postInit(self):
        self._remoteReference = None
        self._id = CityHash64("{}:{}".format(self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, NodeReference):
            raise NotImplementedError()
        return self.id == other.id

    def __lt__(self, other):
        if not isinstance(other, NodeReference):
            raise NotImplementedError()
        return self.id < other.id
    
    def __getattr__(self, attrName: str):
        """
        Turn non-existing methods into remote calls (if at least one identically-named
        method in the local code has been decorated with @remoteMethod).
        """

        if attrName not in remoteMethod.methodNames:
            raise AttributeError(("No such member: '{}'. Additionally, a method with that name "
                                    "is not allowed to be called remotely.").format(attrName))
       
        # create a wrapper for executing the remote call
        @defer.inlineCallbacks
        def remoteCallWrapper(*args, **kwargs):
            # try to get the RemoteReference (might be None)
            try:
                remote = yield self.remote
            except error.ConnectError as err:
                logger.warn(("{}: Remote method call '{}' currently "
                                "cannot be executed: {}").format(self, attrName, err))
                return
            if remote is None:
                logger.warn(("{}: Remote method call '{}' currently cannot be executed: "
                                "No connection to remote host.").format(self, attrName))
                return
            # make the remote call
            deferred = remote.callRemote(attrName, *args, **kwargs)
            try:
                returnValue = yield deferred
                return returnValue
            except pb.PBConnectionLost as err:
                logger.warn("%s: Remote call '%s' failed: Connection to remote node lost.", self, attrName)
            except pb.RemoteError as err:
                logger.warn("%s: Remote call '%s' failed: %s", self, attrName, err)
        
        return remoteCallWrapper
    
    def __hash__(self):
        return hash(self.id)
    
    def __str__(self):
        return "NodeReference({},{})".format(self.host, self.port)
    
    def getStateToCopy(self):
        return (self.host, self.port)
        
    def setCopyableState(self, state):
        host, self._port = state
        self._host = IPv4Address(host)
        self.postInit()
    
    @property
    def host(self):
        if self._host is None:
            raise AttributeError(("host is None! When manually instanciating a NodeReference, "
                                    "both host and port have to be passed to the constructor."))
        return str(self._host)
    
    @property
    def port(self):
        if self._port is None:
            raise AttributeError(("port is None! When manually instanciating a NodeReference, "
                                    "both host and port have to be passed to the constructor."))
        return self._port
    
    @property
    def id(self):
        return self._id
    
    @property
    def remote(self):
        """
        A (maybe deferred) pb.Reference to the corresponding remote node.
        """
        if self._remoteReference is None:
            if (self.host, self.port) in self._remoteReferenceDict:
                # Reference already exists on this host
                self._remoteReference = self._remoteReferenceDict[self.host, self.port]
            else:
                # RemoteReference does not yet exist on this host
                logger.info("%s: Requesting remote reference from %s:%d", self, self.host, self.port)
                factory = pb.PBClientFactory()
                reactor.connectTCP(self.host, self.port, factory)
                deferred = factory.getRootObject()
                deferred.addCallbacks(self._gotRemoteReference, self._failedGettingRemoteReference)
                self._remoteReference = deferred
                self._remoteReferenceDict[self.host, self.port] = deferred

        return linkedDeferred(self._remoteReference) # for simultaneous use in multiple generators
        
    def _failedGettingRemoteReference(self, reason):
        logger.warn("%s: Error getting remote node reference: %s", self, reason)
        self._remoteReference = None
        self._remoteReferenceDict[self.host, self.port] = None
        return reason # pass reason to next callback
    
    def _gotRemoteReference(self, instance: pb.RemoteReference):
        logger.info("%s: Got remote node reference %s", self, instance)
        self._remoteReference = instance
        self._remoteReferenceDict[self.host, self.port] = instance
        return instance # pass reference on to the next callback

pb.setUnjellyableForClass('vaud.core.NodeReference', NodeReference)

class PseudoNodeReference(NodeReference):
    """
    A NodeReference subclass that can be initialized with "lowest" or "highest"
    as the only parameter and serves only for comparison purposes.
    Its instances do not represent remote nodes. Thus, remote will return
    ``None`` and remote calls will fail.
    Note: Both host and port will return fake values!
    """

    def __init__(self, value):
        valueMapping = {"lowest": -1, "highest": 2**64 + 1}
        if value not in valueMapping:
            raise ValueError(("Only 'lowest' or 'highest' are allowed for initializing a PseudoNodeReference. "
                                "'{}' given.").format(value))
        
        self._id = valueMapping[value]

    def __getattr__(self, attrName: str):
        raise AttributeError(("'{}' PseudoNodeReference has no such member: '{}'. As a pseudo NodeReference, "
                                "it can not call the method remotely.").format(self._id, attrName))
    
    def getStateToCopy(self):
        return self.id
        
    def setCopyableState(self, state):
        self.id = state
    
    @property
    def host(self):
        """
        Is always ``None``.
        """
        return None

    @property
    def port(self):
        """
        Is always ``0``.
        """
        return 0
    
    @property
    def value(self) -> str:
        """
        Returns either "lowest" or "highest".
        """
        if self._id == 0:
            return "lowest"
        return "highest"
    
    @property
    def remote(self):
        """
        None, as this instance is a PseudoNodeReference that does not reference a remote node.
        """
        return None

pb.setUnjellyableForClass('vaud.core.PseudoNodeReference', PseudoNodeReference)

def remoteMethod(method):
    """
    A decorator allowing methods to be called remotely.
    It also maintains a set of names of the methods it has been used for.
    """
    method.is_remote_method = True
    remoteMethod.methodNames.add(method.__name__)
    return method

remoteMethod.methodNames = set()

@total_ordering
class Node(pb.Root):
    """
    A local node that offers methods for both local and remote callers.
    In order to make a method callable by a remote caller, it has to be
    decorated with the @remoteMethod decorator.
    Note: Do not initialize nodes yourself, use a NodeFactory for that!
    """

    def __init__(self, port: int, timeoutInterval: int = 1):
        self.reference = NodeReference(thisHost, port)
        self._portObject = reactor.listenTCP(port, pb.PBServerFactory(self))
        
        # Creating a twisted TimerService to call the timeout method periodically
        # Cheat to not call timeout right away (self is probably not ready now)
        def timeoutRunner():
            if timeoutRunner.counter != 0:
                self.timeout()
            timeoutRunner.counter += 1
        timeoutRunner.counter = 0
        self._timer = TimerService(timeoutInterval, timeoutRunner)
        self._timer.startService()
    
    def __getattr__(self, attrName: str):
        """
        Fakes the existence of a 'remote_'-prefixed method for each method
        being decorated with the @remoteMethod decorator.
        """
        if attrName.startswith("remote_") and len(attrName) > 7:
            suffix = attrName[7:]
            if not suffix in dir(self):
                raise AttributeError("There is no member named '{}' or '{}'".format(attrName, suffix))
            if not getattr(self, suffix).is_remote_method:
                raise AttributeError("The method '{}' is not allowed to be called remotely.".format(suffix))
            # the requested method may be called remotely
            return getattr(self, suffix)
        
        # raising an attribute error for all other requests
        raise AttributeError("No such member: '{}'".format(attrName))
    
    def __eq__(self, other):
        if not isinstance(other, (Node, NodeReference)):
            raise NotImplementedError()
        return self.id == other.id

    def __lt__(self, other):
        if not isinstance(other, (Node, NodeReference)):
            raise NotImplementedError()
        return self.id < other.id
    
    def __str__(self):
        return "Node({}:{})".format(self.reference.host, self.reference.port)
    
    @property
    def host(self):
        return self.reference.host
    
    @property
    def port(self):
        return self.reference.port
    
    @property
    def id(self):
        return self.reference.id

    @defer.inlineCallbacks
    def shutdown(self):
        """
        Shuts down the node and returns a deferred that fires
        successfully when shutdown is completed.
        """
        yield self._timer.stopService()
        returnValue = yield self._portObject.loseConnection()
        return returnValue
    
    def timeout(self):
        """
        A periodically called method.
        The time interval is set at construction.
        """

class NodeFactory:
    """
    A factory for Node objects. Only run one NodeFactory instance at a time!
    The factory will create a publically accessible dictionary named `registry`
    and add its Node instances there, indexed by their ports.
    Also, all node instances created will be accessible via the factory's
    localNodes attribute.
    When subclassing, you can override the initNode() method to gain control
    of node initialization.
    """

    def __init__(self, startPort: int):
        self._startPort = startPort
        self._nextPort = startPort
        self.registry = {}
        self.nodes = []

    def newNode(self):
        # get new port
        port = self._nextPort
        self._nextPort += 1
        isFirstNode = (port == self._startPort)
        node = self._initNode(port, isFirstNode)
        self._postInitNode(node, isFirstNode)
        self.registry[port] = node
        self.nodes.append(node)
        return node
    
    def shutdown(self) -> defer.Deferred:
        deferreds = []
        for n in self.nodes:
            deferreds.append(n.shutdown())
        return defer.gatherResults(deferreds)
    
    def _initNode(self, port: int, isFirstNode: bool) -> Node:
        """Override this to control node initialization."""
        return Node(port)
    
    def _postInitNode(self, node: Node, isFirstNode: bool) -> None:
        """Will be called after each _initNode call, providing the new node."""
