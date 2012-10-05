import threading
import Zope2

from zope.component import getUtility
from zope.interface import implements
from zope.event import notify
try:
    # plone < 4.3
    from zope.app.component.hooks import setSite
except:
    from zope.component.hooks import setSite

from zExceptions import BadRequest
from AccessControl.SecurityManagement import noSecurityManager,\
    newSecurityManager, getSecurityManager
from AccessControl.User import SpecialUser
from Products.CMFCore.interfaces import ISiteRoot
from zc.async.interfaces import KEY
from zc.async.job import serial, parallel, Job
from plone.app.async.interfaces import IAsyncDatabase, IAsyncService
from plone.app.async.interfaces import JobSuccess, JobFailure


def makeJob(func, context, *args, **kwargs):
    """Return a job_info tuple."""
    return (func, context, args, kwargs)


def _getAuthenticatedUser():
    """Get user info."""
    user = getSecurityManager().getUser()
    if isinstance(user, SpecialUser):
        return (), None
    acl_users = user.aq_parent
    return acl_users.getPhysicalPath(), user.getId()


def _executeAsUser(context_path, portal_path, uf_path, user_id, func, *args,
    **kwargs):
    """Reconstruct environment and execute func."""
    transaction = Zope2.zpublisher_transactions_manager  # Supports isDoomed
    transaction.begin()
    app = Zope2.app()
    result = None
    try:
        try:
            portal = app.unrestrictedTraverse(portal_path, None)
            if portal is None:
                raise BadRequest(
                    'Portal path %s not found' % '/'.join(portal_path))
            setSite(portal)

            if uf_path:
                acl_users = app.unrestrictedTraverse(uf_path, None)
                if acl_users is None:
                    raise BadRequest(
                        'Userfolder path %s not found' % '/'.join(uf_path))
                user = acl_users.getUserById(user_id)
                if user is None:
                    raise BadRequest('User %s not found' % user_id)
                newSecurityManager(None, user)

            context = portal.unrestrictedTraverse(context_path, None)
            if context is None:
                raise BadRequest(
                    'Context path %s not found' % '/'.join(context_path))
            result = func(context, *args, **kwargs)
            transaction.commit()
        except:
            transaction.abort()
            raise
    finally:
        noSecurityManager()
        setSite(None)
        app._p_jar.close()
    return result


def job_success_callback(result):
    """Fire event on job success."""
    notify(JobSuccess(result))


def job_failure_callback(result):
    """Fire event on job failure."""
    notify(JobFailure(result))


class AsyncService(threading.local):
    """Utility providing async execution services to Plone.
    """
    implements(IAsyncService)

    def __init__(self):
        self._db = None
        self._conn = None

    def getQueues(self):
        """Return the queues container."""
        db = getUtility(IAsyncDatabase)
        if self._db is not db:
            self._db = db
            conn = getUtility(ISiteRoot)._p_jar
            self._conn = conn.get_connection(db.database_name)
            self._conn.onCloseCallback(self.__init__)
        return self._conn.root()[KEY]

    def queueJobInQueue(self, queue, quota_names,
                        func, context, *args, **kwargs):
        """Queue a job in the specified queue."""
        return self.queueJobInQueueWithDelay(
            None, None,
            queue, quota_names,
            func, context, *args, **kwargs)

    def queueJob(self, func, context, *args, **kwargs):
        """Queue a job in the default queue."""
        return self.queueJobInQueue('', ('default',), func, context,
                                    *args, **kwargs)

    def queueJobInQueueWithDelay(self,
                                 begin_by, begin_after,
                                 queue, quota_names,
                                 func, context, *args, **kwargs):
        # can accept both queue and queue_name
        if isinstance(queue, basestring):
            queue = self.getQueues()[queue]
        job = (func, context, args, kwargs)
        # !!! let empty tuples be handled as 'no-quota' !!!
        if quota_names is None:
            quota_names = ('default',)
        return self._queueJobInQueue(queue, quota_names, job,
                                     begin_by, begin_after)

    def queueJobWithDelay(self, begin_by, begin_after, func, context, *args,
        **kwargs):
        return self.queueJobInQueueWithDelay(
            begin_by, begin_after, '', ('default',),
            func, context, *args, **kwargs)

    def wrapJob(self, job_info):
        portal = getUtility(ISiteRoot)
        portal_path = portal.getPhysicalPath()
        uf_path, user_id = _getAuthenticatedUser()
        func, context, args, kwargs = job_info
        context_path = context.getPhysicalPath()
        job = Job(_executeAsUser, context_path, portal_path, uf_path,
            user_id, func, *args, **kwargs)
        return job

    def __queueJobInQueue(self, begin_by, begin_after, queue,
                          quota_names, job):
        if quota_names:
            job.quota_names = quota_names
        job = queue.put(job, begin_by=begin_by, begin_after=begin_after)
        job.addCallbacks(success=job_success_callback,
                         failure=job_failure_callback)
        return job

    def _queueJobInQueue(self, queue, quota_names, job_infos,
                         begin_by=None, begin_after=None):
        """Queue multiple jobs in the specified queue."""
        job = self.wrapJob(job_infos)
        return self.__queueJobInQueue(begin_by, begin_after,
                                      queue, quota_names, job)

    def _queueJobsInQueue(self, queue, quota_names, job_infos, serialize=True,
                          begin_by=None, begin_after=None):
        """Queue multiple jobs in the specified queue."""
        scheduled = [self.wrapJob(job_info) for job_info in job_infos]
        if serialize:
            job = serial(*scheduled)
        else:
            job = parallel(*scheduled)
        return self.__queueJobInQueue(begin_by, begin_after,
                                      queue, quota_names, job)

    def queueSerialJobsInQueue(self, queue, quota_names, *job_infos):
        """Queue serial jobs in the specified queue."""
        return self._queueJobsInQueue(queue, quota_names, job_infos,
            serialize=True)

    def queueParallelJobsInQueue(self, queue, quota_names, *job_infos):
        """Queue parallel jobs in the specified queue."""
        return self._queueJobsInQueue(queue, quota_names, job_infos,
            serialize=False)

    def queueSerialJobs(self, *job_infos):
        """Queue serial jobs in the default queue."""
        queue = self.getQueues()['']
        return self.queueSerialJobsInQueue(queue, ('default',), *job_infos)

    def queueParallelJobs(self, *job_infos):
        """Queue parallel jobs in the default queue."""
        queue = self.getQueues()['']
        return self.queueParallelJobsInQueue(queue, ('default',), *job_infos)
