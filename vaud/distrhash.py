from typing import Dict

from twisted.internet import defer
from twisted.spread import flavors, pb

import vaud.skipplus as skip
from cityhash import CityHash64
from vaud.core import projectOntoUnitInterval, remoteMethod


class Entry(flavors.Copyable, flavors.RemoteCopy):
    """
    A simple key value pair data class for strings.
    It is copyable by Twisted's perspective broker and provides
    non-cryptographic hasing methods.
    """

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def getStateToCopy(self):
        return (self.key, self.value)
        
    def setCopyableState(self, state):
        self.key, self.value = state
    
    def keyHash(self):
        """
        Returns a 64 bit int, produced by hashing the key with CityHash64.
        """
        return CityHash64(self.key)
    
    def unitKeyHash(self):
        """
        Returns the projection of keyHash onto the [0,1) interval.
        """
        return projectOntoUnitInterval(self.keyHash(), 64)

pb.setUnjellyableForClass('vaud.distrhash.Entry', Entry)
    
class HashNode(skip.SkipNode):
    """
    Extends the SkipNode class by adding distributed hash table methods.
    """

    def __init__(self, port):
        super(HashNode, self).__init__(port)
        self.localHashTable = {}
        # predecessor and successor references
        self.pred = skip.lowest
        self.succ = skip.highest

    # Local public operations

    def insert(self, key: str, value: str):
        """Inserts the entry d into the distributed hash table."""
        entry = Entry(key, value)
        self.search(entry, "insert")
    
    def remove(self, key: str):
        keyOnlyEntry = Entry(key, "")
        """Removes the entry specified by `key` from the distributed hash table."""
        self.search(keyOnlyEntry, "delete")
    
    @defer.inlineCallbacks
    def lookup(self, key: str):
        """Executes a lookup against the provided `key` on the distributed hash table."""
        keyOnlyEntry = Entry(key, "")
        result = yield self.search(keyOnlyEntry, "lookup")
        return result
    
    # Local private operations

    def _insert(self, entry: Entry):
        self.localHashTable[entry.key] = entry
    
    def _delete(self, entry: Entry):
        self.localHashTable.pop(entry.key)
    
    def _lookup(self, entry: Entry):
        return self.localHashTable.get(entry.key, None)

    # Remote operations

    @remoteMethod
    def search(self, d: Entry, operationName: str):
        """
        Delegates the search method call to the node that is responsible
        for the key specified in entry d. If a node is responsible, it will
        executes an operation according to `operationName`, providing d.
        Depending on the operation, a (maybe deferred) value might be
        returned by this method.
        """

        def processLocally():
            if operationName == "lookup":
                return self._lookup(d)
            elif operationName == "insert":
                self._insert(d)
            elif operationName == "delete":
                self._delete(d)
        
        @defer.inlineCallbacks
        def delegateTo(v: skip.SkipNodeReference):
            returnValue = yield v.search(d, operationName)
            return returnValue
        
        unitId = projectOntoUnitInterval(self.id, 64) # our position in the [o,1) interval
        unitKey = d.unitKeyHash()

        if self.pred is skip.lowest and unitKey < unitId:
            # We do not have cyclic edges in this implementation, so we have to process the request
            return processLocally()
        if self.succ is skip.highest and unitKey > unitId:
            # The entry is ours
            return processLocally()
        
        # if we reach this line, both pred and succ are references to real nodes
        if not self.pred <= unitKey <= self.succ:
            # determining the node next to unitKey (by id) without overstepping unitKey
            nextNode = None
            if unitKey < self.pred:
                nextNode = min(x for x in self.N if x > unitKey)
            else:
                nextNode = max(x for x in self.N if x < unitKey)
            return delegateTo(nextNode)
        else:
            if unitKey < unitId:
                return delegateTo(self.pred) # entry belongs to our predecessor
            else:
                return processLocally() # entry belongs to us
    
    @remoteMethod
    def handOff(self, v: skip.SkipNodeReference):
        """
        Returns a dict containing this node's entries that are
        to be transferred to a new successor v.
        """
        local = self.localHashTable
        keysToHandOff = [key for key in local.keys() if local[key].unitKeyHash() >= v]
        return {key: local.pop(key) for key in keysToHandOff}
    
    @remoteMethod
    def takeOver(self, hashTable: Dict[str, str]):
        """
        Integrates the passed hashTable dictionary of a leaving node into the localHashTable.
        """
        self.localHashTable.update(hashTable)
    
    @remoteMethod
    @defer.inlineCallbacks
    def linearise(self, u: skip.SkipNodeReference):
        skip.SkipNode.linearise(self, u)
        # update predecessor and successor
        oldPred = self.pred
        self.pred = skip.pred(self.reference, self.N)
        self.succ = skip.succ(self.reference, self.N)
        if self.pred != oldPred and self.pred is not skip.lowest:
            # get our entries from our new predecessor
            hashTable = yield self.pred.handOff(self.reference)
            self.localHashTable.update(hashTable)
    
    @defer.inlineCallbacks
    def shutdown(self):
        if self.pred is not skip.lowest:
            yield self.pred.takeOver(self.localHashTable)
        yield super(HashNode, self).shutdown()

class HashNodeFactory(skip.SkipNodeFactory):

    def _initNode(self, port: int, isFirstNode: bool) -> HashNode:
        return HashNode(port)
