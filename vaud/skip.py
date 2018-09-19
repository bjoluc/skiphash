from bitarray import bitarray
from typing import Set
from vaud.core import CopyableBitArray, Node, NodeReference, remoteMethod, randomBitArray, PseudoNodeReference
from twisted.internet import defer
from twisted.spread import pb

# Define the length of the rs bit string
RS_LENGTH = 8

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
    Returns a copy of the first `i` bits of `v`s random bit string (rs) as a bitarray.
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

def _levelNodes(i: int, v: "SkipNode", x: bool) -> Set(SkipNodeReference):
    """
    Returns {w ∈ N(v) | prefix(i+1, w) = prefix(i, v)◦x}
    """
    # get prefix(i, v)◦x
    pref = prefix(i, v.reference)
    pref.append(x)

    # get {w ∈ N(v) | prefix(i+1, w) = prefix(i, v)◦x}
    return set(w for w in v.N if prefix(i+1, w) == pref)

def levelPred(i: int, v: "SkipNode", x: bool) -> SkipNodeReference:
    """
    levelPred(i, v, x) = pred(v, {w ∈ N(v) | prefix(i+1, w) = prefix(i, v)◦x})
    """
    return pred(v, _levelNodes(i, v, x))

def levelSucc(i: int, v: "SkipNode", x: bool) -> SkipNodeReference:
    """
    levelSucc(i, v, x) = succ(v, {w ∈ N(v) | prefix(i+1, w) = prefix(i, v)◦x})
    """
    return succ(v, _levelNodes(i, v, x))

def low(i: int, v: "SkipNode") -> SkipNodeReference:
    """
    low(i, v) = min{levelPred(i, v, 0), levelPred(i, v, 1)}
    """
    return min(levelPred(i, v, 0), levelPred(i, v, 1))

def high(i: int, v: "SkipNode") -> SkipNodeReference:
    """
    high(i, v) = max{levelPred(i, v, 0), levelPred(i, v, 1)}
    """
    return max(levelSucc(i, v, 0), levelSucc(i, v, 1))

def range(i: int, v: "SkipNode") -> Set[SkipNodeReference]:
    """
    range(i, v) = [low(i, v), high(i, v)]
    """
    return set(w for w in v.N if low(i, v) <= w and w <= high(i, v))

class SkipNode(Node):
    
    def __init__(self, port: int):
        super(SkipNode, self).__init__(port)
        self._rs = CopyableBitArray(randomBitArray(RS_LENGTH)) # random bitstring
        # the self.reference object will serve as the node's id
        # replacing the super constructor's NodeReference by a SkipNodeReference
        self.reference = SkipNodeReference(self.reference.host, port, self.rs)
        self.N = set() # outgoing neighborhood
    
    @remoteMethod(constantReturnValue=True)
    def rs(self):
        """
        The node's random bit string. For connecting a new node only.
        If a SkipNodeReference has been passed to you, you will
        want to use its rs attribute, instead of maybe dealing with a deferred.
        """
        return self._rs
