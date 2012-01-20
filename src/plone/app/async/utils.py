from transaction import begin, commit
from zope import component
from zc.async.testing import wait_for_result
from zc.twist import Failure
from plone.app.async.interfaces import IAsyncService


def wait_for_all_jobs(seconds=6, assert_successful=True):
    """Wait for all jobs in the queue to complete"""
    begin()
    service = component.getUtility(IAsyncService)
    queue = service.getQueues()['']
    for job in queue:
        wait_for_result(job, seconds)
        if assert_successful:
            assert not isinstance(job.result, Failure), str(job.result)
    commit()


def queue(job):
    service = component.getUtility(IAsyncService)
    queue = service.getQueues()['']
    return queue.put(job)
