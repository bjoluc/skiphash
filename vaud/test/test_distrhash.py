import logging
import time

import pytest
import pytest_twisted
from pytest_mock import mocker
from twisted.internet import defer, reactor
from twisted.python import log

from vaud.core import sleep
from vaud.distrhash import HashNode, HashNodeFactory

observer = log.PythonLoggingObserver()
observer.start()

# pylint: disable=maybe-no-member

@pytest_twisted.inlineCallbacks
def test_operations(caplog, mocker):
    caplog.set_level(logging.DEBUG, logger='vaud.core')
    caplog.set_level(logging.DEBUG, logger='vaud.skip')
    caplog.set_level(logging.WARN, logger='twisted')

    factory = HashNodeFactory(33000)

    for _ in range(4):
        factory.newNode()
    
    yield sleep(2)

    nodes = factory.nodes

    for i in range(4):
        nodes[0].insert("key" + str(i), "value" + str(i))
    
    yield sleep(2)
    
    for i in range(4):
        result = yield nodes[3].lookup("key" + str(i))
        assert result.value == "value" + str(i)
    
    yield sleep(2)

    for i in range(4):
        nodes[2].remove("key" + str(i))
    
    yield sleep(2)
    
    for i in range(4):
        result = yield nodes[1].lookup("key" + str(i))
        assert result == None

    yield factory.shutdown()
