from typing import List

from vaud.skipplus import RS_BIT_LENGTH, SkipNode, SkipNodeReference, prefix


class Analyzer():
    """
    A class for creating structured representations of skip plus graph data.
    It offers the following public attributes:
    `nodeToIndexMap`, `prefixToNodesMap` and `prefixes`.
    """

    def __init__(self, nodes: List[SkipNode]):
        self.nodes = sorted(nodes) # sort nodes by id
        # mapping nodes to their horizontal positional index
        self.nodeToIndexMap = dict((n, index) for index, n in enumerate(self.nodes))
        self.prefixToNodesMap = self._calculatePrefixToNodesMap()
        # a list of all prefixes with actual nodes, sorted by prefix length, descending
        self.prefixes = sorted(self.prefixToNodesMap.keys(), key=lambda rs: len(rs), reverse=True)
        
    def _calculatePrefixToNodesMap(self):
        """
        Returns a dict that maps an rs-prefix to lists of nodes with that rs-prefix.
        Prefixes with empty node lists are not contained.
        """
        map = {}
        for node in self.nodes:
            rs = node.rs
            # iterate over rs prefix length
            for prefixLength in range(0, len(rs)-1):
                rsPrefix = prefix(prefixLength, rs)
                if rsPrefix in map:
                    map[rsPrefix].append(node)
                else:
                    map[rsPrefix] = [node]
        return map
    
                
            
