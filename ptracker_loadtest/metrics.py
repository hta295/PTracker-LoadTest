from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class Metrics:
    """Object which stores load metrics and receives writes from worker threads. It is then read to print the results
    """

    def __init__(self, num_workers: int):
        # Total request latency (measured from application-layer)
        self.num_workers = num_workers
        self.total_latency_seconds = 0.
        self.total_num_attempts = 0
        self.total_num_successes = 0
        self.latency_metric_lock = threading.Lock()
        self.count_metrics_lock = threading.Lock()

    def add_latency(self, latency_seconds: float) -> None:
        """Submits a new response latency to the Metrics object

        Adding a new latency metric updates the latency total.

        :param latency_seconds: the new latency in seconds
        :returns: None
        """
        with self.latency_metric_lock:
            self.total_latency_seconds += latency_seconds

    def add_success(self, num_attempts: int) -> None:
        """Submits a new success as well as the number of attempts to the Metrics object

        Adding a new num_attempts metric updates the attempt count's total.
        and increments the Metrics object's success count

        :param num_attempts: the number of attempts to add to count
        :returns: None
        """
        with self.count_metrics_lock:
            self.total_num_successes += 1
            self.total_num_attempts += num_attempts
