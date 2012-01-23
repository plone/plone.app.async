import BTrees.OOBTree
from datetime import timedelta
from zc.async.job import RetryCommonFourTimes


class RetryWithDelay(RetryCommonFourTimes):
    """A retry policy that will retry on internal/transaction
    exceptions four times like normal, but also retry on job
    errors after a configurable delay.

    Defaults to a delay of 15 minutes with 8 retries.
    """

    max_retries = 8
    job_exceptions = RetryCommonFourTimes.internal_exceptions + (
        ((Exception,), 'job_error', max_retries, 0, 0, 0,),
        )
    datacache_key = 'job_error'

    def __init__(self, delay=timedelta(minutes=15)):
        self.delay = delay

    def __call__(self, job):
        self.parent = self.__parent__ = job
        self.data = BTrees.family32.OO.BTree()
        return self

    def jobError(self, failure, data_cache):
        if not data_cache:
            data_cache.update(self.data)

        # handle normal retry logic
        res = self._process(failure, data_cache, self.job_exceptions)

        # if we're retrying and it's not an internal exception,
        # introduce the delay
        if res and not failure.check(*self.internal_exceptions):
            return self.delay
