from bitarray import bitarray
from typing import Set
from vaud.core import CopyableBitArray, Node, NodeReference, remoteMethod, randomBitArray, PseudoNodeReference
from twisted.internet import defer
from twisted.spread import pb

# Define the length of the rs bit string
RS_BYTE_LENGTH = 2
RS_BIT_LENGTH = RS_BYTE_LENGTH * 8

lowest = PseudoNodeReference("lowest")
highest = PseudoNodeReference("highest")

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
        superState, self.rs = state
        super(SkipNodeReference, self).setCopyableState(superState)
    
    @property
    def rs(self):
        if self._rs is None:
            raise AttributeError(("rs is None! When manually instanciating a SkipNodeReference, "
                                    "rs has to be passed to the constructor."))
        return self._rs
    
    @property.setter('rs')
    def setRs(self, rs: CopyableBitArray):
        self._rs = rs

pb.setUnjellyableForClass('vaud.core.SkipNodeReference', SkipNodeReference)

# general skip helper functions

def prefix(i: int, v: SkipNodeReference) -> CopyableBitArray:
    """
    Returns a copy of the first `i` bits of `v`s random
    bit string (rs) as a bitarray.
    """
    return v.rs.copy()[:i]

def pred(v: SkipNodeReference, W: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    pred(v, w) = arg max (w∈W ∪ {lowest}) {w < v}
    """
    return max([w for w in W if w < v].append(lowest))

def succ(v: SkipNodeReference, W: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    succ(v, W) = arg min (w∈W ∪ {highest}) {w > v}
    """
    return min([w for w in W if w > v].append(highest))

def _levelNodes(i: int, v: SkipNodeReference, x: bool, N: Set[SkipNodeReference]) -> Set(SkipNodeReference):
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
    vPrefix = prefix(i,v)
    l = low(i, v, N)
    h = high(i, v, N)
    return set(w for w in N if prefix(i, w) == vPrefix and l <= w and w <= h)

def commonPrefixLength(v: bitarray, w: bitarray) -> int:
    """
    Returns the number of bits of the longest common
    prefix of v's and w's random bit strings.
    """
    i = 0
    while i < min(len(v), len(w)) and v[i] == w[i]:
        i += 1
    return i

def longestCommonPrefixNode(w: SkipNodeReference, W: Set[SkipNodeReference]) -> SkipNodeReference:
    """
    Returns the SkipNodeReference of the node in W that has
    the longest common random bit string prefix with w.
    """
    return max(W, key=lambda x: commonPrefixLength(x.rs, w.rs))

class SkipNode(Node):
    
    def __init__(self, port: int):
        super(SkipNode, self).__init__(port)
        self._rs = CopyableBitArray(randomBitArray(RS_BYTE_LENGTH)) # random bitstring
        # the self.reference object will serve as the node's id
        # replacing the super constructor's NodeReference by a SkipNodeReference
        self.reference = SkipNodeReference(self.reference.host, port, self._rs)
        self.N = set() # outgoing neighborhood
        self._ranges = {} # range for each level i < RS_BIT_LENGTH - 1

        # a set of all nodes (SkipNodeReferences) that are currently
        # in at least one of this node's ranges
        self._nodesInRanges = set()
    
    @remoteMethod(constantReturnValue=True)
    def rs(self):
        """
        The node's random bit string. For connecting a new node only.
        If a SkipNodeReference has been passed to you, you will
        want to use its rs attribute, instead of maybe dealing with a deferred.
        """
        return self._rs
    
    # "Build-Skip" methods
    
    def updateRanges(self):
        nodesInRanges = set()
        for i in range(RS_BIT_LENGTH-1):
            currentLevelRange = skipRange(i, self.reference, self.N)
            self._ranges[i] = currentLevelRange
            nodesInRanges.union(currentLevelRange)
        self._nodesInRanges = nodesInRanges
    
    def timeout(self):
        # See Chapter 5, Slide 169 f.
        for i in range(RS_BIT_LENGTH-1):
            # partition range of level i by left and right nodes
            leftRange = []
            rightRange = []
            for x in self._ranges[i]:
                if x < self.reference:
                    leftRange.append(x)
                if x > self.reference:
                    rightRange.append(x)

            # introduce nodes as shown below
            # leftRange: v1 -> v2 -> ... -> self
            # rightRange: self <- ... <- v(n-1) <- vn

            leftRange.sort()
            rightRange.sort(reverse=True)

            # Part a: Linearizing
            for r in (leftRange, rightRange):
                for i in range(len(r)-1):
                    r[i].linearise(r[i+1])
                if len(r) > 0:
                    # introduce closest node to self
                    r[-1].linearise(self.reference)
        
            # Part b: Bridging (as on slide 170)
            # - left nodes to first right node
            # - right nodes to first left node

            for range1, range2 in ((leftRange, rightRange), (rightRange, leftRange)):
                if len(range2) > 0:
                    closestRange2Node = range2[-1] # last node in right resp. left range
                    for v in range1:
                        if closestRange2Node in skipRange(i, v, self.N):
                            # this node thinks that closestRange2Node is in v's range
                            v.linearise(closestRange2Node)
    
    @remoteMethod
    def linearise(self, u: SkipNodeReference):
        # See Chapter 5, Slide 171
        if u != self.reference and u not in self.N:
            self.N.add(u)
            self.updateRanges()
            undesirableNodes = self.N.difference(self._nodesInRanges) # nodes that are not in any range now
            self.N = self._nodesInRanges # only keep the relevant nodes in our neighborhood
            # delegate the undesirable nodes
            for w in undesirableNodes:
                delegationDestination = longestCommonPrefixNode(w, self.N)
                delegationDestination.linearise(w)