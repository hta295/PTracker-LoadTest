from __future__ import annotations

import logging
import math
import threading

logger = logging.getLogger(__name__)


class Metrics:
    """Singleton which stores load metrics and receives writes from worker threads. It is then read by output threads.
    """

    _instance = None    # type: Metrics

    def add_latency(self, latency: float) -> None:
        """Submits a new response latency to the Metrics object

        Adding a new latency metric updates the latency's moving average

        :param latency: the new latency
        :returns: None
        """
        with self.average_latency_lock:
            self.average_latency = self.average_latency / 2 + latency / 2 if not math.isnan(self.average_latency) \
                                     else latency

    @classmethod
    def get_instance(cls) -> Metrics:
        """Returns the single Metrics instance

        :returns: reference to the sole Metrics instance
        """
        return Metrics._instance if Metrics._instance else Metrics()

    def __init__(self):
        if self._instance:
            raise TypeError(' '.join([
                "Metrics is a singleton and has already been instantiated.",
                "Call Metrics.get_instance() instead"
            ]))
        else:
            # On first call to constructor, set singleton instance
            logger.debug("Creating new Metrics instance")
            Metrics._instance = self

            # Moving average request latency (measured from application-layer)
            self.average_latency = float('nan')
            self.average_latency_lock = threading.Lock()
