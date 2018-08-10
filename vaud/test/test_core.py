import pytest, logging, time
from pytest_mock import mocker
from vaud.core import Node

@pytest.fixture
def nodes(caplog, mocker):
    caplog.set_level(logging.DEBUG, logger='vaud.core')
    nodes = [Node(33098+i, 0.1) for i in range(2)]

    yield nodes

    for n in nodes:
        n.shutdown()

def test_transmissions(caplog, mocker, nodes):
    caplog.set_level(logging.DEBUG, logger='vaud.core')

    for n in nodes:
        mocker.patch.object(n, "_inputHandler")

    n1, n2 = nodes
    msg = "Test message"

    n1.send(msg, n2.address)
    time.sleep(.001)
    n2._inputHandler.assert_called_with(msg)

    n2.send(msg, n1.address)
    time.sleep(.001)
    n1._inputHandler.assert_called_with(msg)

def test_timer(caplog, mocker, nodes):
    caplog.set_level(logging.DEBUG, logger='vaud.core')

    for n in nodes:
        mocker.patch.object(n, "_timeout")
        n._timeout.assert_not_called()
    
    for i in range(1,4):
        time.sleep(0.1001)
        for n in nodes:
            assert n._timeout.call_count == i
