import argparse
import csv
import logging

from functools import partial
from threading import Thread
from typing import List, Tuple

from .metrics import Metrics
from .ptracker_session import PTrackerSession
from .thread_factory import ThreadFactory
from .utils.secrets import TEST_USER, TEST_PASSWORD

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

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
    parser.add_argument('-n', '--num_workers', type=int, required=False, default=1,
                        help='Maximum number of worker threads to spin up')
    parser.add_argument('-f', '--output_csv_filename', type=str, required=False,
                        help='Filename of the csv file to write to')

    return parser


def _measure_index_latency(session: PTrackerSession, metrics: Metrics) -> None:
    """Measures the response latency when user retrieves the PTracker index and writes it to Metrics

    :param session: the http Session
    :returns: tuple containing (the measured latency in seconds [float], num_retries [int])
    """
    num_attempts = 0
    latency = 0.
    index_page = None
    while not index_page:
        try:
            index_page, latency = session.get_index()
        except Exception:
            # Silently swallow exceptions when connecting
            pass
        finally:
            num_attempts += 1
    metrics.add_latency(latency)


def create_threads(args: argparse.Namespace) -> Tuple[List[Thread], List[Thread]]:
    """Creates the threads needed for the load test

    This function distinguishes between helper threads and worker threads. ALL
    helper threads should be started before the test begins. The test strategy can
    determine how to start the worker threads.

    :param args: the cli args
    :returns: tuple(helper_thread_list, worker_thread_list
    """
    # Get an authenticated PTracker session for the workers to use
    session = PTrackerSession(args.root_url)
    session.authenticate(TEST_USER, TEST_PASSWORD)

    metrics = Metrics.get_instance()
    csv_writer = csv.writer(open(args.output_csv_filename, 'w')) if args.output_csv_filename else None
    printer = ThreadFactory.create_printer(args.num_workers, csv_writer, metrics)
    work_function = partial(_measure_index_latency, session, metrics)
    workers = [ThreadFactory.create_worker(work_function) for _ in range(args.num_workers)]
    return [printer], workers


def run(cli_args: List[str]) -> None:
    """Runs load testing workflow against PTracker server

    :param cli_args: list of cli args as strings (i.e. sys.argv)
    :returns: None
    """
    setup_logging()
    arg_parser = get_parser()
    helpers, workers = create_threads(arg_parser.parse_args(cli_args))
    logging.debug("Starting the load test...")
    [h.start() for h in helpers]
    [w.start() for w in workers]
