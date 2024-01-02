import multiprocessing.queues
import logging

import _queue


class Queue(multiprocessing.queues.Queue):

    _name = "unknown"

    def __init__(self, ctx, name):
        self._name = name
        logging.getLogger().info("Queue %s[%s]/init" % (ctx, self._name))
        super().__init__(ctx=ctx)

    def put(self, msg, block=True, timeout=False):
        logging.getLogger().debug("Queue %s/put: %s" % (self._name, msg))
        return super().put(msg, block, timeout)

    def get(self, block=True, timeout=False):
        try:
            msg = super().get(block, timeout)
        except _queue.Empty:
            return None
        if msg:
            logging.getLogger().debug("Queue %s/get: %s" % (self._name, msg))
        return msg

