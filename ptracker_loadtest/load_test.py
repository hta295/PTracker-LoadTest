import argparse
import csv
import logging
import time

from threading import active_count, Thread
from typing import List, Optional, Tuple

from .ptracker_session import PTrackerSession
from .utils.secrets import TEST_USER, TEST_PASSWORD

from .metrics import Metrics

# Number of seconds for printer thread to wait to print updated test details
PRINTER_SLEEP_TIME = 1

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


def measure_index_latency(session: PTrackerSession) -> Tuple[float, int]:
    """Measures the response latency when user retrieves the PTracker index

    :param session: the http Session
    :returns: tuple containing (the measured latency in seconds [float], num_retries [int])
    """
    num_attempts = 0
    latency = 0.
    while num_attempts == 0:
        try:
            _, latency = session.get_index()
        except Exception:
            # Silently swallow exceptions when connecting
            pass
        finally:
            num_attempts += 1
    return latency, num_attempts


def worker_thread_loop(session: PTrackerSession) -> None:
    """Control-loop for worker threads.

    Worker threads generate load for the PTracker web service. Currently, this
    consists of repeatedly retrieving the list of productivity intervals. The
    server workflow for this is:

    Client --request--> Web Server --get_all_intervals--> DB --response--> Web Server --response--> Client

    TODO: support for other testing modes

    :param session: the authenticated test Session
    :returns: None
    """
    while True:
        latency, _ = measure_index_latency(session)
        Metrics.get_instance().add_latency(latency)


def printer_thread_loop(num_workers: int, output_csv_filename: Optional[str]) -> None:
    """Control-loop for printer thread.

    Currently, loop logs the testing details and writes data to a csv_file

    :param num_workers: maximum number of worker threads
    :param output_csv_filename: filename for csv file to write details to, or None if we should not write to a csv
    """
    metrics = Metrics.get_instance()
    header_list = ['THREAD COUNT', 'AVG LATENCY (s)']
    # In addition to worker threads, there should be 1 printer thread and 1 main threads
    num_other_threads = 2
    logger.info('\t'.join([f'{detail:<12}' for detail in header_list]))
    csv_writer = None   # type: Optional[csv.DictWriter]
    if output_csv_filename:
        output_csv = open(output_csv_filename, 'w')
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(header_list)
    while True:
        time.sleep(PRINTER_SLEEP_TIME)
        details_list = [
            f'{active_count()}/{num_workers + num_other_threads}',
            f'{metrics.average_latency:.2f}'
        ]
        logger.info('\t'.join([f'{detail:<12}' for detail in details_list]))
        if csv_writer:
            csv_writer.writerow(details_list)


# noinspection PyListCreation
def create_threads(session: PTrackerSession, args: argparse.Namespace) -> List[Thread]:
    """Creates a new list of Threads, sorted from highest priority first (e.g. printer) to lowest (e.g. workers)

    :param session: the PTracker session
    :param args: the user's cli arguments, used to parametrize the test
    :returns: the sorted list of Threads
    """
    threads = []    # type: List[Thread]
    # Add a printer thread to write testing results
    threads.append(Thread(target=printer_thread_loop, args=(args.num_workers, args.output_csv_filename)))
    # Add worker threads to simulate the client traffic
    threads += [Thread(target=worker_thread_loop, args=(session,)) for _ in range(args.num_workers)]
    return threads


def start_test(args:argparse.Namespace) -> None:
    """Starts the load test

    Spins up a printer thread to write out test results, and a user-defined number of
    worker threads to simulate client load on PTracker

    :param args: the user's arguments from cli
    :returns: None
    """
    # Get an authenticated PTracker session for the rest of the test
    session = PTrackerSession(args.root_url)
    try:
        session.authenticate(TEST_USER, TEST_PASSWORD)
    except Exception:
        logger.exception("Failed to authenticate to PTracker")
        exit(1)
    logging.debug(f"Got authenticated http session: {str(session)}")

    threads = create_threads(session, args)

    logger.debug(f"Starting {len(threads)} thread")
    [t.start() for t in threads]


def run(cli_args: List[str]) -> None:
    """Runs load testing workflow against PTracker server

    :param cli_args: list of cli args as strings (i.e. sys.argv)
    :returns: None
    """
    setup_logging()
    arg_parser = get_parser()
    start_test(arg_parser.parse_args(cli_args))
