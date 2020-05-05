import pytest
import requests

from unittest.mock import MagicMock, patch

import ptracker_loadtest.load_test as load
import ptracker_loadtest.thread_factory as thread_factory

from ptracker_loadtest.metrics import Metrics
from ptracker_loadtest.ptracker_session import PTrackerSession
from ptracker_loadtest.utils.custom_types import TimedResponse

FLOAT_TEST_EQUALITY_TOLERANCE = .0001


# load_test.py tests

def test_setup_logging_config():
    mock_logging = MagicMock()
    mock_config = MagicMock()
    mock_logging.basicConfig = mock_config
    with patch.object(load, 'logging', mock_logging):
        load.setup_logging()
        mock_config.assert_called_once()


def test_get_parser_required_false():
    parser = load.get_parser()
    cli_args = []
    with pytest.raises(SystemExit):
        parser.parse_args(cli_args)


def test_get_parser_required_minimal():
    parser = load.get_parser()
    cli_args = ['-u', 'foo', '-f', 'out']
    args = parser.parse_args(cli_args)
    assert args.root_url == 'foo'
    assert args.output_csv_filename == 'out'


def test_get_parser_required_optional():
    parser = load.get_parser()
    cli_args = ['-u', 'foo', '-n', '3', '-f', 'out']
    args = parser.parse_args(cli_args)
    assert args.root_url == 'foo'
    assert args.num_iterations == 3
    assert args.output_csv_filename == 'out'


def test__measure_index_latency_success_first_time():
    mock_add_latency = MagicMock()
    mock_add_success = MagicMock()
    mock_metrics = MagicMock()
    mock_metrics.add_latency = mock_add_latency
    mock_metrics.add_success = mock_add_success
    mock_index = MagicMock()
    timed_response = TimedResponse(response=mock_index, seconds_elapsed=1.)
    mock_get_index = MagicMock(return_value=timed_response)
    mock_session = MagicMock()
    mock_session.get_index = mock_get_index
    load._measure_index_latency(mock_session, mock_metrics)
    mock_add_latency.assert_called_once_with(1.)
    mock_add_success.assert_called_once_with(1)


def test__measure_index_latency_success_after_retries():
    mock_add_latency = MagicMock()
    mock_add_success = MagicMock()
    mock_metrics = MagicMock()
    mock_metrics.add_latency = mock_add_latency
    mock_metrics.add_success = mock_add_success
    mock_index = MagicMock()
    timed_response = TimedResponse(response=mock_index, seconds_elapsed=2.)
    mock_get_index = MagicMock(side_effect=[ConnectionError, ConnectionError, timed_response])
    mock_session = MagicMock()
    mock_session.get_index = mock_get_index
    load._measure_index_latency(mock_session, mock_metrics)
    mock_add_latency.assert_called_once_with(2.)
    mock_add_success.assert_called_once_with(3)


def test_create_workers_authenticated_session():
    mock_session = MagicMock()
    mock_constructor = MagicMock(return_value=mock_session)
    mock_auth = MagicMock()
    mock_session.authenticate = mock_auth
    with patch.object(load, 'PTrackerSession', mock_constructor):
        load.create_workers(1, 'foo', MagicMock(), 1)
        mock_constructor.assert_called_with('foo')
        mock_auth.assert_called_once()


def test_write_metrics_writes_to_csv():
    mock_metrics = MagicMock()
    mock_metrics.num_workers = 2
    mock_metrics.total_num_successes = 5
    mock_metrics.total_latency_seconds = 3.45312
    mock_metrics.total_num_attempts = 10
    mock_writer = MagicMock()
    mock_writerow = MagicMock()
    mock_writer.writerow = mock_writerow
    details_list = ['2', '5', '3.45', '10']
    load.write_metrics(mock_writer, mock_metrics)
    mock_writerow.assert_called_once_with(details_list)


def test__create_load_test_csv_writer_returns_writer():
    mock_file = MagicMock()
    mock_writer = MagicMock()
    mock_csv = MagicMock()
    mock_csv.writer = MagicMock(return_value=mock_writer)
    with patch.object(load, 'csv', mock_csv):
        actual = load._create_load_test_csv_writer(mock_file)
        mock_csv.writer.assert_called_once_with(mock_file)
        assert actual == mock_writer


def test__create_load_test_csv_writer_prepends_some_header():
    mock_file = MagicMock()
    mock_writer = MagicMock()
    mock_csv = MagicMock()
    mock_csv.writer = MagicMock(return_value=mock_writer)
    with patch.object(load, 'csv', mock_csv):
        load._create_load_test_csv_writer(mock_file)
        mock_writer.writerow.assert_called_once()


# metrics.py tests

def test_num_workers_metrics():
    metrics = Metrics(20)
    assert metrics.num_workers == 20


def test_add_latency_first():
    metrics = Metrics(1)
    first_latency = 1.0
    assert metrics.total_latency_seconds == pytest.approx(0., FLOAT_TEST_EQUALITY_TOLERANCE)
    metrics.add_latency(first_latency)
    assert metrics.total_latency_seconds == pytest.approx(first_latency, FLOAT_TEST_EQUALITY_TOLERANCE)


def test_add_latency_multiple():
    metrics = Metrics(1)
    first_latency = 8.0
    second_latency = 4.0
    third_latency = 2.0
    metrics.add_latency(first_latency)
    metrics.add_latency(second_latency)
    metrics.add_latency(third_latency)
    assert metrics.total_latency_seconds == pytest.approx(14., FLOAT_TEST_EQUALITY_TOLERANCE)


def test_add_success_first():
    metrics = Metrics(1)
    first_num_attempts = 2
    assert metrics.total_num_successes == 0
    assert metrics.total_num_attempts == 0
    metrics.add_success(first_num_attempts)
    assert metrics.total_num_successes == 1
    assert metrics.total_num_attempts == 2


def test_add_success_multiple():
    metrics = Metrics(1)
    first_num_attempts = 20
    second_num_attempts = 10
    third_num_attempts = 5
    metrics.add_success(first_num_attempts)
    metrics.add_success(second_num_attempts)
    metrics.add_success(third_num_attempts)
    assert metrics.total_num_successes == 3
    assert metrics.total_num_attempts == 35


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
    assert timed_response.seconds_elapsed == pytest.approx(1., FLOAT_TEST_EQUALITY_TOLERANCE)
    assert timed_response.response == mock_index
    mock_get.assert_called_with('foo')


# thread_factory.py tests

def test_factory_not_instantiable():
    with pytest.raises(TypeError):
        thread_factory.ThreadFactory()


def test_create_timed_worker():
    mock_thread = MagicMock()
    mock_thread_constructor = MagicMock(return_value=mock_thread)
    mock_work_func = MagicMock()
    lifetime = 5
    with patch.object(thread_factory, 'Thread', mock_thread_constructor):
        actual = thread_factory.ThreadFactory.create_timed_worker(lifetime, mock_work_func)
        mock_thread_constructor.assert_called_once_with(target=thread_factory.ThreadFactory._worker_thread_loop,
                                                        args=(lifetime, mock_work_func))
        assert actual == mock_thread
