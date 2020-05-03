import math
import pytest
import requests

from unittest.mock import MagicMock, patch

import ptracker_loadtest.load_test as load
import ptracker_loadtest.metrics as metrics

from ptracker_loadtest.ptracker_session import PTrackerSession

FLOAT_TEST_TOLERANCE = .0001


# load_test.py tests

def test_get_parser_required_false():
    parser = load.get_parser()
    cli_args = []
    with pytest.raises(SystemExit):
        parser.parse_args(cli_args)


def test_get_parser_required_minimal():
    parser = load.get_parser()
    cli_args = ['-u', 'foo']
    args = parser.parse_args(cli_args)
    assert args.root_url == 'foo'


def test_get_parser_required_optional():
    parser = load.get_parser()
    cli_args = ['-u', 'foo', '-n', '3', '-f', 'out']
    args = parser.parse_args(cli_args)
    assert args.root_url == 'foo'
    assert args.num_workers == 3
    assert args.output_csv_filename == 'out'


# metrics.py tests

@pytest.fixture
def metrics_container():
    """Returns a Metrics instance whose average latency is reset
    """
    m = metrics.Metrics.get_instance()
    m.average_latency = float('nan')


def test_metrics_get_instance_singleton():
    first_instance = metrics.Metrics.get_instance()
    second_instance = metrics.Metrics.get_instance()
    assert first_instance == second_instance


def test_metrics_get_instance_second_constructor_fails():
    first_instance = metrics.Metrics.get_instance()
    with pytest.raises(TypeError):
        metrics.Metrics()


def test_add_latency_first(metrics_container):
    first_latency = 1.0
    m = metrics.Metrics.get_instance()
    assert math.isnan(m.average_latency)
    m.add_latency(first_latency)
    assert m.average_latency == pytest.approx(first_latency, FLOAT_TEST_TOLERANCE)


def test_add_latency_moving_average(metrics_container):
    first_latency = 8.0
    second_latency = 4.0
    third_latency = 2.0
    m = metrics.Metrics.get_instance()
    m.add_latency(first_latency)
    m.add_latency(second_latency)
    m.add_latency(third_latency)
    assert m.average_latency == pytest.approx(4., FLOAT_TEST_TOLERANCE)


# ptracker_session.py tests

@pytest.fixture
def session():
    return PTrackerSession('foo')


def test_ptracker_session_inheritance(session):
    assert isinstance(session, PTrackerSession)
    assert isinstance(session, requests.Session)


def test_authenticate(session):
    def _set_csrf_some(*args, **kwargs):
        session.cookies = {'csrftoken': 'csrf'}

    mock_get = MagicMock(side_effect=_set_csrf_some)
    session.get = mock_get
    mock_post = MagicMock()
    session.post = mock_post

    session.authenticate('user', 'password')
    expected_post_data = {
        'username': 'user',
        'password': 'password',
        'csrfmiddlewaretoken': 'csrf'
    }
    mock_get.assert_called_with('foo/login/')
    mock_post.assert_called_with('foo/login/', expected_post_data)


@patch('time.time', MagicMock(side_effect=[1., 2.]))
def test_get_index(session):
    mock_index = MagicMock()
    mock_get = MagicMock(return_value=mock_index)
    session.get = mock_get
    print(session.get('foo'))

    timed_response = session.get_index()
    assert timed_response.seconds_elapsed == pytest.approx(1., FLOAT_TEST_TOLERANCE)
    assert timed_response.response == mock_index
    mock_get.assert_called_with('foo')
