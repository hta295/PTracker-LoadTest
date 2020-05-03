import argparse
import bs4
import csv
import logging
import requests
import threading
import time

from typing import List, Optional

from .utils import secrets
from .utils.secrets import TEST_USER, TEST_PASSWORD

from .metrics import Metrics

# Number of seconds for printer thread to wait to print updated test details
PRINTER_SLEEP_TIME = 1

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logger = logging.getLogger(__name__)


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


def get_authenticated_session(root_url: str, user: str, password: str) -> requests.Session:
    """Logs into PTracker with test credentials and returns the resulting, authenticated Session.

    :param root_url: PTracker's root url as a string (e.g. 'http://localhost:8000')
    :param user: the test username
    :param password: the test password
    :returns: a Session authenticated to PTracker
    """
    login_url = f'{root_url}/login/'
    session = requests.Session()
    # Get CSRF token from page
    session.get(login_url)
    csrftoken = None
    if 'csrftoken' in session.cookies:
        # Django 1.6 and up
        csrftoken = session.cookies['csrftoken']
    # Post to login form
    data = {'username': user, 'password': password, 'csrfmiddlewaretoken': csrftoken}
    session.post(login_url, data)
    return session


def get_my_interval_strs(root_url: str, session: requests.Session) -> List[str]:
    """Get's the current user's intervals as strings and return the List

    Updates the response latency metric

    :param root_url: PTracker's root url as a string
    :param session: the http Session
    :returns: the List of interval strings
    """
    # Time http call to the PTracker index
    start_time = time.time()
    index_page = None   # type: Optional[requests.Response]
    while not index_page or index_page.status_code != 200:
        try:
            index_page = session.get(root_url)
        except Exception:
            # Silently swallow exceptions when connecting
            continue
    end_time = time.time()
    # Update the moving average for latency
    Metrics.get_instance().add_latency(end_time - start_time)
    # Get the list of interval strings
    soup = bs4.BeautifulSoup(index_page.text, 'html.parser')
    interval_strs = [elem.text for elem in soup.find_all('li')]
    return interval_strs


def worker_thread_loop(root_url: str, session: requests.Session) -> None:
    """Control-loop for worker threads.

    Worker threads generate load for the PTracker web service. Currently, this
    consists of repeatedly retrieving the list of productivity intervals. The
    server workflow for this is:

    Client --request--> Web Server --get_all_intervals--> DB --response--> Web Server --response--> Client

    TODO: support for other testing modes

    :param root_url: PTracker's root url as a string
    :param session: the authenticated test Session
    :returns: None
    """
    while True:
        get_my_interval_strs(root_url, session)


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
            f'{threading.active_count()}/{num_workers + num_other_threads}',
            f'{metrics.average_latency:.2f}'
        ]
        logger.info('\t'.join([f'{detail:<12}' for detail in details_list]))
        if csv_writer:
            csv_writer.writerow(details_list)


def run(cli_args: List[str]):
    """Runs load testing workflow against PTracker server

    :param cli_args: list of cli args as strings (i.e. sys.argv)
    :returns: None
    """
    # Setup logging
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

    # Get cli arguments
    arg_parser = get_parser()
    args = arg_parser.parse_args(cli_args)

    # Get an authenticated PTracker session for the rest of the test
    session = None
    try:
        session = get_authenticated_session(args.root_url, TEST_USER, TEST_PASSWORD)
    except Exception:
        logger.exception("Failed to authenticate to PTracker")
        exit(1)
    logging.debug(f"Got authenticated http session: {str(session)}")

    # Create a bunch of threads to make http requests to the server
    workers = [threading.Thread(target=worker_thread_loop,
                                args=(args.root_url, session)) for _ in range(args.num_workers)]

    # Create a printer thread to print the current load test details
    logger.info(f"Starting 1 printer thread")
    printer = threading.Thread(target=printer_thread_loop, args=(args.num_workers, args.output_csv_filename))

    # Disable logging WARNING's in workers' downstream calls to urllib3 to prevent cluttering logs
    requests_logger = logging.getLogger('urllib3')
    requests_logger.setLevel(logging.ERROR)

    # Startup the threads and begin the test
    logger.info(f"Starting 1 printer thread and {len(workers)} worker threads")
    printer.start()
    [t.start() for t in workers]
