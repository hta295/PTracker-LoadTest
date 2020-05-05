import logging
import time

from threading import Thread
from typing import Callable

logger = logging.getLogger(__name__)


class ThreadFactory:

    """Factory used to create threads used in PTracker load test
    """

    def __init__(self):
        raise TypeError("ThreadFactory is not instantiable")

    @staticmethod
    def _worker_thread_loop(lifetime_seconds: int, func: Callable[[], None]) -> None:
        """Control-loop for worker threads.

        Worker threads generate load for the PTracker web service. This is
        implemented by calling some function in a tight loop

        :param lifetime_seconds: number of seconds (clock-time) to let the loop run
        :param func: the function to call
        :returns: None
        """
        # Call function until lifetime has gone by
        start_time_seconds = time.time()
        while time.time() - start_time_seconds < lifetime_seconds:
            func()

    @staticmethod
    def create_timed_worker(lifetime_seconds: int, work_function: Callable[[], None]) -> Thread:
        """Creates a new worker Thread

        Workers are just threads that call some function in a tight loop

        :param lifetime_seconds: number of seconds (clock-time) to let the thread run
        :param work_function: the function that workers will call to generate work
        :returns: the worker Thread
        """
        return Thread(target=ThreadFactory._worker_thread_loop, args=(lifetime_seconds, work_function))
