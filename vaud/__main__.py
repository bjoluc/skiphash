# Main script to run a number of nodes and optionally
# display a visualization of the local nodes and
# their neighbors.

import argparse
import logging
import sys

from twisted.application.internet import TimerService
from twisted.internet import reactor

from vaud.analyze import Analyzer
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

# parse arguments

parser = argparse.ArgumentParser(prog='skiphash', description='A distributed hash table based on a skip plus overlay network')
parser.add_argument('-n', '--nodes', type=int, default=1,
                    help='The number of nodes to be run locally. Defaults to 1.')
parser.add_argument('-p', '--port', type=int, default=33000,
                    help='The port to be used by the first local node. Defaults to 33000.')
parser.add_argument('-c', '--connect', type=str, default="",
                    help='If set, the local nodes will be connected to the host:port tuple specified after this flag.')
parser.add_argument('-v', '--visualize', action='store_true',
                    help='Runs a graphic user interface with a visualization of the skip graph formed by the local nodes.')
args = parser.parse_args()

# setup nodes

if not args.connect:
    factory = SkipNodeFactory(args.port)
else:
    host, port = args.connect.split(':')
    factory = SkipNodeFactory(args.port, host, int(port))

for _ in range(args.nodes):
    factory.newNode()

# setup visualization
visualize = args.visualize

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

analyzer = Analyzer(nodes)
def startVisualizer():
    Visualizer(nodes, analyzer)
reactor.callFromThread(startVisualizer)

'''
# ah, if you need a timer:
def updateView():
    pass

timer = TimerService(1, v.redraw)  # use some of your object's update method of course ;)
timer.startService()
'''
# Starting the Twisted reactor, runs the nodes
reactor.run()
