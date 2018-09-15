import logging
import time

import pytest
import pytest_twisted
from pytest_mock import mocker
from twisted.internet import reactor, defer
from twisted.internet.address import IPv4Address
from twisted.python import log

from vaud.core import Node

observer = log.PythonLoggingObserver()
observer.start()

# pylint: disable=maybe-no-member

@pytest.fixture
def nodes(caplog, mocker):
    caplog.set_level(logging.DEBUG, logger='vaud.core')
    caplog.set_level(logging.DEBUG, logger='twisted')
    nodes = [Node(reactor, 33000+i, 0.1) for i in range(2)]

    yield nodes

    deferreds = []
    for n in nodes:
        deferreds.append(n.shutdown())
    pytest_twisted.blockon(defer.gatherResults(deferreds))

def test_transmissions(caplog, mocker, nodes):
    caplog.set_level(logging.DEBUG, logger='vaud.core')

    #for n in nodes:
    #    mocker.patch.object(n, "_timeout")
    
    n1, n2 = nodes

    n1.callRemoteMethod(n2.address, "testMethod")
    time.sleep(.5)

    n2.callRemoteMethod(n1.address, "testMethod")
    time.sleep(.5)

    # TODO mocking and assertions

def test_timer(caplog, mocker, nodes):
    caplog.set_level(logging.DEBUG, logger='vaud.core')

    for n in nodes:
        mocker.patch.object(n, "_timeout")
        n._timeout.assert_not_called()
    
    for i in range(1,4):
        time.sleep(0.1001)
        for n in nodes:
            assert n._timeout.call_count == i
