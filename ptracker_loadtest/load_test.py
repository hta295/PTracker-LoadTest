import argparse
import csv
import logging

from functools import partial
from threading import Thread
from typing import List, TextIO

from .metrics import Metrics
from .ptracker_session import PTrackerSession
from .thread_factory import ThreadFactory
from .utils.custom_types import TimedResponse
from .utils.secrets import TEST_USER, TEST_PASSWORD

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configures logging for process

    Disables WARNING's from urllib3 to de-clutter logs

    :returns: None
    """
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    requests_logger = logging.getLogger('urllib3')
    requests_logger.setLevel(logging.ERROR)


def get_parser() -> argparse.ArgumentParser:
    """Configures and returns an argparse parser for this application.

    :returns: the configured parser
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--root_url', type=str, required=True,
                        help='The root URL for the PTracker web service')
    parser.add_argument('-n', '--num_iterations', type=int, required=False, default=5,
                        help='The number of test iterations.')
    parser.add_argument('-l', '--iteration_length_seconds', type=int, required=False, default=10,
                        help='The length of an iteration in seconds')
    parser.add_argument('-w', '--start_num_workers', type=int, required=False, default=5,
                        help='Number of workers in first iteration')
    parser.add_argument('-s', '--num_workers_skip', type=int, required=False, default=5,
                        help='Number of workers to add each iteration')
    parser.add_argument('-f', '--output_csv_filename', type=str, required=True,
                        help='Filename of the csv file to write to')

    return parser


def _measure_index_latency(session: PTrackerSession, metrics: Metrics) -> None:
    """Measures the response latency when user retrieves the PTracker index and writes it to Metrics

    :param session: the http Session
    :returns: tuple containing (the measured latency in seconds [float], num_retries [int])
    """
    num_attempts = 0
    timed_response = TimedResponse(response=None, seconds_elapsed=float('nan'))
    while not timed_response.response:
        try:
            timed_response = session.get_index()
        except Exception:
            # Silently swallow exceptions when connecting
            pass
        finally:
            num_attempts += 1
    metrics.add_latency(timed_response.seconds_elapsed)
    metrics.add_success(num_attempts)


def create_workers(thread_lifetime_seconds: int, root_url: str, metrics: Metrics, num_workers: int) -> List[Thread]:
    """Creates the threads needed for the load test

    :param thread_lifetime_seconds: number of seconds to let each thread run for (real/clock-time
    :param root_url: root url of the PTracker web service
    :param metrics: the Metrics object the threads should write to
    :param num_workers: the number of workers to create
    :returns: the list of threads
    """
    # Get an authenticated PTracker session for the workers to use
    session = PTrackerSession(root_url)
    session.authenticate(TEST_USER, TEST_PASSWORD)

    work_function = partial(_measure_index_latency, session, metrics)
    return [ThreadFactory.create_timed_worker(thread_lifetime_seconds, work_function) for _ in range(num_workers)]


def write_metrics(csv_writer: csv.DictWriter, metrics: Metrics) -> None:
    """Writes metrics from a test out to a csv file as a row

    :param csv_writer: the DictWriter for the csv file
    :param metrics: the Metrics from the test
    :returns: None
    """
    details_list = [
        f'{metrics.num_workers}',
        f'{metrics.total_num_successes}',
        f'{metrics.total_latency_seconds:.2f}',
        f'{metrics.total_num_attempts}'
    ]
    csv_writer.writerow(details_list)


def _create_load_test_csv_writer(file: TextIO) -> csv.DictWriter:
    """Create a csv writer used to write test results

    Side-effect is to prepend the data header to the csv

    :param file: the output file
    :returns: the csv writer
    """
    writer = csv.writer(file)
    header_list = ['NUM ACTIVE WORKERS', 'TOTAL NUM SUCCESSES', 'TOTAL LATENCY (s)', 'TOTAL NUM ATTEMPTS']
    writer.writerow(header_list)
    return writer


def run(cli_args: List[str]) -> None:
    """Runs load testing workflow against PTracker server

    Main entry point to load tester

    :param cli_args: list of cli args as strings (i.e. sys.argv)
    :returns: None
    """
    setup_logging()

    args = get_parser().parse_args(cli_args)
    num_workers = args.start_num_workers
    num_iterations = args.num_iterations
    num_workers_skip = args.num_workers_skip
    test_length_seconds = args.iteration_length_seconds
    root_url = args.root_url

    with open(args.output_csv_filename, 'w') as output_csv:
        csv_writer = _create_load_test_csv_writer(output_csv)

        for iteration_num in range(1, num_iterations + 1):
            metrics = Metrics(num_workers)
            workers = create_workers(test_length_seconds, root_url, metrics, num_workers)

            logger.info(f'Starting test #{iteration_num} with {num_workers} workers for {test_length_seconds} s')
            [w.start() for w in workers]
            [w.join() for w in workers]
            logger.info(f'Finished with test #{iteration_num}.')

            write_metrics(csv_writer, metrics)
            output_csv.flush()
            num_workers += num_workers_skip
