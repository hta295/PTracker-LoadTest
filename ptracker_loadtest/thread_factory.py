import csv
import logging
import time

from threading import active_count, Thread
from typing import Callable, Optional, TextIO

from .metrics import Metrics

# Number of seconds for printer thread to wait to print updated test details
PRINTER_SLEEP_TIME = 1

logger = logging.getLogger(__name__)


class ThreadFactory:

    """Factory used to create threads used in PTracker load test
    """

    def __init__(self):
        raise TypeError("ThreadFactory is not instantiable")

    @staticmethod
    def _printer_thread_loop(csv_file: TextIO, metrics: Metrics) -> None:
        """Control-loop for printer thread.

        Currently, the loop just writes data to a csv_file

        :param csv_file: the csv file to output to
        :param metrics: the Metrics object to read from
        :returns: None
        """
        csv_writer = csv.writer(csv_file)
        header_list = ['NUM ACTIVE WORKERS', 'TOTAL NUM SUCCESSES', 'TOTAL LATENCY (s)', 'TOTAL NUM ATTEMPTS']
        csv_writer.writerow(header_list)

        # In addition to worker threads, there should be 1 printer thread and 1 main threads
        num_non_worker_threads = 2
        while True:
            time.sleep(PRINTER_SLEEP_TIME)
            details_list = [
                f'{active_count() - num_non_worker_threads}',
                f'{metrics.total_num_successes}',
                f'{metrics.total_latency_seconds:.2f}',
                f'{metrics.total_num_attempts}'
            ]
            csv_writer.writerow(details_list)
            csv_file.flush()

    @staticmethod
    def create_printer(csv_file: TextIO, metrics: Metrics) -> Thread:
        """Creates a printer Thread which is responsible for writing out test results

        :param csv_file: the csv file to output to
        :param metrics: the Metrics container to read from
        :returns: the printer Thread
        """
        return Thread(target=ThreadFactory._printer_thread_loop, args=(csv_file, metrics))

    @staticmethod
    def _worker_thread_loop(func: Callable[[], None]) -> None:
        """Control-loop for worker threads.

        Worker threads generate load for the PTracker web service. This is
        implemented by calling some function in a tight loop

        Client --request--> Web Server --get_all_intervals--> DB --response--> Web Server --response--> Client

        TODO: support for other testing modes (e.g. w/ jitter?)

        :param func: the function to call
        :returns: None
        """
        while True:
            func()

    @staticmethod
    def create_worker(work_function: Callable[[], None]) -> Thread:
        """Creates a new worker Thread

        Workers are just threads that call some function in a tight loop

        :param work_function: the function that workers will call to generate work
        :returns: the worker Thread
        """
        return Thread(target=ThreadFactory._worker_thread_loop, args=(work_function,))
