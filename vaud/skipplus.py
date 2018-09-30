import logging
# general skip helper functions
from typing import Set, Union

from bitarray import bitarray
from twisted.internet import defer
from twisted.spread import pb

from vaud.core import (CopyableBitArray, Node, NodeFactory, NodeReference,
                       PseudoNodeReference, eprint, randomBitArray,
                       remoteMethod)

# Define the length of the rs bit string
RS_BYTE_LENGTH = 2
RS_BIT_LENGTH = RS_BYTE_LENGTH * 8

lowest = PseudoNodeReference("lowest")
highest = PseudoNodeReference("highest")

logger = logging.getLogger(__name__)

class SkipNodeReference(NodeReference):
    """
    Extends the NodeReference class by a node's random bit string (rs).
    """
    
    def __init__(self, host: str = None, port: int = None, rs: CopyableBitArray = None):
        super(SkipNodeReference, self).__init__(host, port)
        self._rs = rs
    
    def getStateToCopy(self):
        return (super(SkipNodeReference, self).getStateToCopy(), self.rs)
        
    def setCopyableState(self, state):
        superState, self._rs = state
        super(SkipNodeReference, self).setCopyableState(superState)
    
    @property
    def rs(self):
        if self._rs is None:
            raise AttributeError(("rs is None! When manually instanciating a SkipNodeReference, "
                                    "rs has to be passed to the constructor."))
        return self._rs
    
    @rs.setter
    def rs(self, rs: CopyableBitArray):
        self._rs = rs

pb.setUnjellyableForClass('vaud.skipplus.SkipNodeReference', SkipNodeReference)


def prefix(i: int, v: Union["SkipNode", SkipNodeReference, bitarray]) -> CopyableBitArray:
    """
    Returns a copy of the first `i` bits of `v`s random
    bit string (rs) as a bitarray.
    """
    if isinstance(v, (SkipNode, SkipNodeReference)):
        rs = v.rs
    else:
        rs = v
    return rs.copy()[:i]

def pred(v: SkipNodeReference, W: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    pred(v, w) = arg max (w∈W ∪ {lowest}) {w < v}
    """
    return max([w for w in W if w < v] + [lowest])

def succ(v: SkipNodeReference, W: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    succ(v, W) = arg min (w∈W ∪ {highest}) {w > v}
    """
    if len(W) == 0:
        W = []
    return min([w for w in W if w > v] + [highest])

def _levelNodes(i: int, v: SkipNodeReference, x: bool, N: Set[SkipNodeReference]) -> Set[SkipNodeReference]:
    """
    Returns {w ∈ N | prefix(i+1, w) = prefix(i, v)◦x}
    """
    # get prefix(i, v)◦x
    pref = prefix(i, v)
    pref.append(x)

    # get {w ∈ N(v) | prefix(i+1, w) = prefix(i, v)◦x}
    return set(w for w in N if prefix(i+1, w) == pref)

def levelPred(i: int, v: SkipNodeReference, x: bool, N: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    levelPred(i, v, x, N) = pred(v, {w ∈ N | prefix(i+1, w) = prefix(i, v)◦x})
    """
    return pred(v, _levelNodes(i, v, x, N))

def levelSucc(i: int, v: SkipNodeReference, x: bool, N: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    levelSucc(i, v, x, N) = succ(v, {w ∈ N | prefix(i+1, w) = prefix(i, v)◦x})
    """
    return succ(v, _levelNodes(i, v, x, N))

def low(i: int, v: SkipNodeReference, N: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    low(i, v, N) = min{levelPred(i, v, 0, N), levelPred(i, v, 1, N)}
    """
    return min(levelPred(i, v, 0, N), levelPred(i, v, 1, N))

def high(i: int, v: SkipNodeReference, N: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    high(i, v, N) = max{levelPred(i, v, 0, N), levelPred(i, v, 1, N)}
    """
    return max(levelSucc(i, v, 0, N), levelSucc(i, v, 1, N))

def skipRange(i: int, v: SkipNodeReference, N: Set[SkipNodeReference]) -> Set[SkipNodeReference]:
    """
    range(i, v, N) = [low(i, v, N), high(i, v, N)]
    """
    vPrefix = prefix(i, v)
    l = low(i, v, N)
    h = high(i, v, N)
    return set(w for w in N if prefix(i, w) == vPrefix and l <= w and w <= h)

def filterByPrefix(i: int, v: SkipNodeReference, nodes: Set[SkipNodeReference]) -> Set[SkipNodeReference]:
    """
    Returns {w ∈ nodes | prefix(i, w) = prefix(i, v)}
    """
    vPrefix = prefix(i, v)
    return set(w for w in nodes if prefix(i, w) == vPrefix)

def commonPrefixLength(v: bitarray, w: bitarray) -> int:
    """
    Returns the number of bits of the longest common
    prefix of v's and w's random bit strings.
    """
    i = 0
    while i < min(len(v), len(w)) and v[i] == w[i]:
        i += 1
    return i

def longestCommonPrefixNodes(w: SkipNodeReference, W: Set[SkipNodeReference]) -> Set[SkipNodeReference]:
    """
    Returns a set of SkipNodeReferences of the nodes in W that have
    the longest common random bit string prefix with w.
    """
    longestCommonPrefixLength = max(map(lambda x: commonPrefixLength(x.rs, w.rs), W))
    longestCommonPrefix = prefix(longestCommonPrefixLength, w.rs)
    return set(filter(lambda x: prefix(longestCommonPrefixLength, x.rs) == longestCommonPrefix, W))

class SkipNode(Node):
    
    def __init__(self, port: int):
        super(SkipNode, self).__init__(port)
        self._rs = CopyableBitArray(randomBitArray(RS_BYTE_LENGTH)) # random bitstring
        # the self.reference object will serve as the node's id
        # replacing the super constructor's NodeReference by a SkipNodeReference
        self.reference = SkipNodeReference(self.reference.host, port, self._rs)
        self.N = set() # outgoing neighborhood

        # range for each level i < RS_BIT_LENGTH - 1
        self.ranges = dict((i, set()) for i in range(RS_BIT_LENGTH-1)) 

        # a set of all nodes (SkipNodeReferences) that are currently
        # in at least one of this node's ranges
        self.nodesInRanges = set()
    
    @remoteMethod
    def getRs(self):
        """
        The node's random bit string. For connecting a new node only.
        If a SkipNodeReference has been passed to you, you will
        want to use its rs attribute, instead of maybe dealing with a deferred.
        """
        return self._rs
    
    @property
    def rs(self):
        return self._rs
    
    # "Build-Skip" methods
    
    def updateRanges(self):
        nodesInRanges = set()
        for i in range(RS_BIT_LENGTH-1):
            currentLevelRange = skipRange(i, self.reference, self.N)
            self.ranges[i] = currentLevelRange
            nodesInRanges.union(currentLevelRange)
        self.nodesInRanges = nodesInRanges
    
    def timeout(self):
        # Introducing this node to all of our neighbors - not mentioned on the slides.
        # Still seems to be necessary in order to guarantee strong connectedness.
        for n in self.N:
            n.linearise(self.reference)

        # See Chapter 5, Slide 169 f.
        for i in range(RS_BIT_LENGTH-1):
            # partition neighborhood of level i by left and right nodes
            levelNeighborhood = filterByPrefix(i, self.reference, self.ranges[i])
            leftNodes = []
            rightNodes = []
            for x in levelNeighborhood:
                if x < self.reference:
                    leftNodes.append(x)
                if x > self.reference:
                    rightNodes.append(x)

            # introduce nodes as shown below
            # leftNodes: v1 -> v2 -> ... -> self
            # rightNodes: self <- ... <- v(n-1) <- vn

            leftNodes.sort()
            rightNodes.sort(reverse=True)

            # Part a: Linearizing
            for r in (leftNodes, rightNodes):
                for i in range(len(r)-1):
                    r[i].linearise(r[i+1])
                if len(r) > 0:
                    # introduce closest node to self
                    r[-1].linearise(self.reference)
        
            # Part b: Bridging (as on slide 170)
            # - left nodes to closest right node
            # - right nodes to closest left node

            for side1, side2 in ((leftNodes, rightNodes), (rightNodes, leftNodes)):
                if len(side2) > 0:
                    closestRange2Node = side2[-1] # last node in right resp. left nodes
                    for v in side1:
                        #if closestRange2Node in skipRange(i, v, self.N):
                            # this node thinks that closestRange2Node is in v's range
                        v.linearise(closestRange2Node)
    
    @remoteMethod
    def linearise(self, u: SkipNodeReference):
        logger.debug("%s.linearise(%s) is called.", self, u)
        # See Chapter 5, Slide 171
        if u != self.reference and u not in self.N:
            self.N.add(u)
            self.updateRanges()
            if len(self.nodesInRanges) == 0:
                # There are no nodes in our ranges.
                # Let's better keep our current neighbors instead of destroying the connectedness!
                pass
            else:
                undesirableNodes = self.N.difference(self.nodesInRanges) # nodes that are not in any range now
                self.N = self.nodesInRanges # only keep the skip+ neighbors in our neighborhood
                # delegate the undesirable nodes
                for w in undesirableNodes:
                    # use the longestCommonPrefixNodes with the minimum id difference (the "closest" ones)
                    nodes = longestCommonPrefixNodes(w, self.N)
                    delegationDestination = min(nodes, key=lambda x: abs(x.id - w.id))
                    delegationDestination.linearise(w)

class SkipNodeFactory(NodeFactory):
    """
    A NodeFactory for SkipNodes.
    The node that was previously created will be introduced
    to the next node that will be created.
    If entryNodeHost and entryNodePort are specified, the specified
    remote node will be introduced to the first node that will be created.
    """
    def __init__(self, startPort: int, entryNodeHost: str = None, entryNodePort: int = None):
        super(SkipNodeFactory, self).__init__(startPort)
        self._entryNodeHost = entryNodeHost
        self._entryNodePort = entryNodePort
        self.entryNodeReference = None # if configured, will store the SkipNodeReference, once the rs value has arrived
        if entryNodeHost is not None and entryNodePort is not None:
            # create a NodeReference to ask the entry node for its random bit string
            entryNodeReference = NodeReference(entryNodeHost, entryNodePort)
            deferredRs = entryNodeReference.getRs() # request random bit string
            deferredRs.addCallbacks(self._gotEntryNodeRs, self._failedGettingEntryNodeRs)
    
    def _gotEntryNodeRs(self, rs: CopyableBitArray):
        self.entryNodeReference = SkipNodeReference(self._entryNodeHost, self._entryNodePort, rs)
        if len(self.nodes) > 0:
            self.nodes[0].introduce(self.entryNodeReference)
    
    def _failedGettingEntryNodeRs(self, reason: str):
        logger.warn("Failed to get the entry node's random bit string! This host will not be connected to any other host.")
    
    def _initNode(self, port: int, isFirstNode: bool) -> Node:
        return SkipNode(port)
    
    def _postInitNode(self, node: Node, isFirstNode: bool) -> None:
        if isFirstNode:
            if self.entryNodeReference is not None:
                node.linearise(self.entryNodeReference)
        else:
            node.linearise(self.nodes[-1].reference)
