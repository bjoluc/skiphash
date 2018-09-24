# Main script to run a number of nodes and optionally
# display a visualization of the local nodes and
# their neighbors.

import logging
import sys

from twisted.application.internet import TimerService
from twisted.internet import reactor

from vaud.skipplus import SkipNode, SkipNodeFactory
from vaud.view import Visualizer

# For twisted reactor method calls:
# pylint: disable=maybe-no-member

# setup stdout logging

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
rootLogger.addHandler(streamHandler)

factory = SkipNodeFactory(33000)

# input values (will be parsed from cli later)
numNodes = 10
visualize = True

for _ in range(numNodes):
    factory.newNode()

# Here we go - those are your nodes! ;)
nodes = sorted(factory.nodes)
#nodes = factory.nodes

# Some examples:
myNode = nodes[0]

myNodeRs = myNode.rs # Subtype of https://pypi.org/project/bitarray/
myNodeId = myNode.id # IP port tuple like "1.2.3.4:1234"
# do not compare ids, compare references (myNode.reference)
# if you need one of those
myNodeIp = myNode.host
myNodePort = myNode.port

# Set of all neighbors (as NodeReferences)
neighbors = myNode.N

# Set of Skip+ neighbors
stableNeighbors = myNode.nodesInRanges

# Dict of ranges
level0Range = myNode.ranges[0] # set of NodeReferences in range 0

# Lots of space for your stuff :P
print("now my stuff starts")


v = Visualizer(nodes)



# ah, if you need a timer:
def updateView():
    pass
timer = TimerService(1, updateView)  # use some of your object's update method of course ;)
timer.startService()

# Starting the Twisted reactor, runs the nodes
reactor.run()
