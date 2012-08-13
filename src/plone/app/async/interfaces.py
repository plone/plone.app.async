from zope import interface
from zope.component.interfaces import IObjectEvent


class IInitAsync(interface.Interface):

    def init():
        """ init zc.async """


class IAsyncDatabase(interface.Interface):
    """ zc.async database """


class IAsyncService(interface.Interface):
    """Utility"""

    def getQueues():
        """Return the queue container."""

    def queueJob(func, context, *args, **kwargs):
        """Queue a job."""

    def queueJobWithDelay(begin_by, begin_after, func, context, *args,
        **kwargs):
        """Queue a job with a delay. See zc.async for more information"""

    def queueSerialJobs(*job_infos):
        """Queue several jobs, to be run serially

        job_info is a tuple with (func, context, args, kwargs).
        """

    def queueParallelJobs(*job_infos):
        """Queue several jobs, to be run in parallel

        job_info is a tuple with (func, context, args, kwargs).
        """

    def queueJobInQueue(queue, quota_names, func, context, *args, **kwargs):
        """Queue a job in a specific queue."""

    def queueSerialJobsInQueue(queue, quota_names, *job_infos):
        """Queue several jobs in a specific queue, to be run serially

        job_info is a tuple with (func, context, args, kwargs).
        """

    def queueParallelJobsInQueue(queue, quota_names, *job_infos):
        """Queue several jobs in a specific queue, to be run in parallel

        job_info is a tuple with (func, context, args, kwargs).
        """


class IQueueReady(IObjectEvent):
    """Queue is ready"""


class QueueReady(object):
    interface.implements(IQueueReady)

    def __init__(self, object):
        self.object = object


class IJobSuccess(IObjectEvent):
    """Job was completed successfully"""


class JobSuccess(object):
    interface.implements(IJobSuccess)

    def __init__(self, object):
        self.object = object


class IJobFailure(IObjectEvent):
    """Job has failed"""


class JobFailure(object):
    interface.implements(IJobFailure)

    def __init__(self, object):
        self.object = object
