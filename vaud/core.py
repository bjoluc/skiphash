import logging

from twisted.internet import defer, reactor
from twisted.spread import flavors, pb

from vaud import thisHost

logger = logging.getLogger(__name__)

# For twisted reactor method calls:
# pylint: disable=maybe-no-member

class NodeFactory:
    """
    A factory for node objects. Only run one NodeFactory instance at a time!
    If localNodeRegistry is not set to false, the factory will index
    its Node instances by ports and hand them out on request.
    """

    def __init__(self, startPort: int, localNodeRegistry: bool = True):
        self._nextPort = startPort
        self.hasRegistry = localNodeRegistry

        if localNodeRegistry:
            self._registry = {}

    def newNode(self):
        # get new port
        port = self._nextPort
        self._nextPort += 1
        node = Node(port)
        if self.hasRegistry:
            self._registry[port] = node
        self.afterCreation(node)
        return node
    
    def afterCreation(self, node: "Node"):
        """
        Will be called after a node has been created,
        providing the new node instance.
        Use this in your subclasses.
        """

class NodeReference(flavors.Copyable, flavors.RemoteCopy):
    """
    A NodeReference stores a host and a port of a distant node
    and will on demand connect to that node.
    Also, remote node methods can be invoked directly on a NodeReference
    and will be executed by the referenced node, returning a (maybe) deferred for
    the remote method's result.
    """

    _remoteReferenceDict = {}
    """A dictionary for storing existing RemoteReference instances, indexed by their host and port"""

    def __init__(self, host: str = None, port: int = None):
        self._host = host
        self._port = port
        self._remoteReference = None
        self._cache = {}
    
    def __getattr__(self, attrName: str):
        """
        Turn non-existing methods into remote calls (if at least one identically-named
        method in the local code has been decorated with @remoteMethod).
        """
        if attrName not in remoteMethod.methodNames:
            raise AttributeError("A method named '{}' is not allowed to be called remotely.".format(attrName))
        
        cacheable = attrName in remoteMethod.constantReturnValueMethodNames
        if cacheable and attrName in self._cache:
            return self._cache[attrName]
       
        # create a wrapper for executing the remote call
        @defer.inlineCallbacks
        def remoteCallWrapper(*args, **kwargs):
            remote = yield self.remote
            deferred = remote.callRemote(attrName, *args, **kwargs)
            if cacheable:
                self._cache[attrName] = deferred
            returnValue = yield deferred
            if cacheable:
                self._cache[attrName] = returnValue
            return returnValue
        
        return remoteCallWrapper
    
    def __eq__(self, obj):
        if not isinstance(obj, NodeReference):
            raise NotImplementedError()
        return self.host == obj.host and self.port == obj.port
    
    def getStateToCopy(self):
        return (self.host, self.port)
        
    def setCopyableState(self, state):
        self._host, self._port = state
    
    @property
    def host(self):
        if self._host is None:
            raise AttributeError(("host is None! When manually instanciating a NodeReference, "
                                    "both host and port have to be passed to the constructor."))
        return self._host
    
    @property
    def port(self):
        if self._port is None:
            raise AttributeError(("port is None! When manually instanciating a NodeReference, "
                                    "both host and port have to be passed to the constructor."))
        return self._port
    
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
                logger.info("Requesting remote node reference from %s:%d", self.host, self.port)
                factory = pb.PBClientFactory()
                reactor.connectTCP(self.host, self.port, factory)
                deferred = factory.getRootObject()
                deferred.addCallbacks(self._gotRemoteReference, self._failedGettingRemoteReference)
                self._remoteReference = deferred
                self._remoteReferenceDict[self.host, self.port] = deferred

        return self._remoteReference
        
    def _failedGettingRemoteReference(self, reason):
        logger.warn("Error retrieving remote node: %s", reason)
        self._remoteReference = None
        self._remoteReferenceDict[self.host, self.port] = None
        return reason # pass reason to next callback
    
    def _gotRemoteReference(self, instance: flavors.Referenceable):
        logger.info("Got remote node reference %s", instance)
        self._remoteReference = instance
        self._remoteReferenceDict[self.host, self.port] = instance
        return instance # pass reference on to the next callback

pb.setUnjellyableForClass(NodeReference, NodeReference)


def remoteMethod(constantReturnValue = False):
    """
    A decorator factory allowing methods to be called remotely.
    It also maintains a set of names of the methods it has been used for.
    If constantReturnValue is set to true, a NodeReference will only call
    the remote method once, cache the result and further use the cached result.
    """
    def decorator(method):
        method.is_remote_method = True
        methodName = method.__name__
        remoteMethod.methodNames.add(methodName)
        if constantReturnValue:
            remoteMethod.constantReturnValueMethodNames.add(methodName)
        return method
    
    return decorator

remoteMethod.methodNames = set()
remoteMethod.constantReturnValueMethodNames = set()
    
class Node(pb.Root):
    """
    A local node that offers methods for both local and remote callers.
    In order to make a method callable by a remote caller, it has to be
    decorated with the @remoteMethod decorator.
    """

    def __init__(self, port: int):
        self.reference = NodeReference(thisHost, port)
        self._portObject = reactor.listenTCP(port, pb.PBServerFactory(self))
    
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
        
        # delegating the lookup to object for all other requests
        return object.__getattr__(self, attrName)

    def shutdown(self):
        """
        Shuts down the node and returns a deferred that fires
        successfully when shutdown is completed.
        """
        return self._portObject.loseConnection()
