import csv
import logging
import time

from threading import active_count, Thread
from typing import Callable, Optional

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
    def _printer_thread_loop(num_workers: int, csv_writer: Optional[csv.DictWriter], metrics: Metrics) -> None:
        """Control-loop for printer thread.

        Currently, loop logs the testing details and writes data to a csv_file

        :param num_workers: maximum number of worker threads
        :param csv_writer: the csv writer object to output to, or None if no csv output
        :param metrics: the Metrics object to read from
        :returns: None
        """
        header_list = ['THREAD COUNT', 'AVG LATENCY (s)']
        logger.info('\t'.join([f'{detail:<12}' for detail in header_list]))
        if csv_writer:
            csv_writer.writerow(header_list)

        # In addition to worker threads, there should be 1 printer thread and 1 main threads
        num_other_threads = 2
        while True:
            time.sleep(PRINTER_SLEEP_TIME)
            details_list = [
                f'{active_count()}/{num_workers + num_other_threads}',
                f'{metrics.average_latency:.2f}'
            ]
            logger.info('\t'.join([f'{detail:<12}' for detail in details_list]))
            if csv_writer:
                csv_writer.writerow(details_list)

    @staticmethod
    def create_printer(num_workers: int, csv_writer: Optional[csv.DictWriter], metrics: Metrics) -> Thread:
        """Creates a printer Thread which is responsible for writing out test results

        :param num_workers: maximum number of worker threads
        :param csv_writer: the csv writer object to output to, or None if no csv output
        :returns: the printer Thread
        """
        return Thread(target=ThreadFactory._printer_thread_loop, args=(num_workers, csv_writer, metrics))

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
