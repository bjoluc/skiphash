# Main script to run a number of nodes and optionally
# display a visualization of the local nodes and
# their neighbors.

import logging
import sys

from twisted.internet import reactor

from vaud.skip import SkipNode, SkipNodeFactory

# For twisted reactor method calls:
# pylint: disable=maybe-no-member

# setup stdout logging

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

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

reactor.run()