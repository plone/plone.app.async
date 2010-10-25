import Zope2
from threading import local
from zope.component import getUtility
from zope.interface import implements
from zope.event import notify
from zope.app.component.hooks import setSite
from Acquisition import aq_inner, aq_parent
from zExceptions import BadRequest
from AccessControl.SecurityManagement import noSecurityManager,\
    newSecurityManager
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from zc.async.interfaces import KEY
from zc.async.job import serial, parallel, Job
from plone.app.async.interfaces import IAsyncDatabase, IAsyncService
from plone.app.async.interfaces import JobSuccess, JobFailure


def makeJob(func, context, *args, **kwargs):
    """Return a job_info tuple."""
    return (func, context, args, kwargs)


def _executeAsUser(portal_path, context_path, user_id, uf_path, func, *args, **kwargs):
    transaction = Zope2.zpublisher_transactions_manager # Supports isDoomed
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

            acl_users = app.unrestrictedTraverse(uf_path, None)
            if acl_users is None:
                raise BadRequest(
                    'Userfolder path %s not found' % '/'.join(uf_path))
            user = acl_users.getUserById(user_id)
            if user is None:
                raise BadRequest('User %s not found' % user_id)
            if not hasattr(user, 'aq_base'):
                user = user.__of__(acl_users)
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
    ev = JobSuccess(result)
    notify(ev)


def job_failure_callback(result):
    ev = JobFailure(result)
    notify(ev)


class AsyncService(local):
    implements(IAsyncService)

    def __init__(self):
        self._db = None
        self._conn = None

    def getQueues(self):
        db = getUtility(IAsyncDatabase)
        if self._db is not db:
            self._db = db
            conn = getUtility(ISiteRoot)._p_jar
            self._conn = conn.get_connection(db.database_name)
            self._conn.onCloseCallback(self.__init__)
        return self._conn.root()[KEY]

    def queueJobInQueue(self, queue, quota_names, func, context, *args, **kwargs):
        portal = getUtility(ISiteRoot)
        portal_path = portal.getPhysicalPath()
        pm = getToolByName(portal, 'portal_membership')
        user = pm.getAuthenticatedMember()
        user_id = user.getId()
        uf_path = user.aq_parent.aq_parent.getPhysicalPath()
        context_path = context.getPhysicalPath()
        job = Job(_executeAsUser, portal_path, context_path, user_id, uf_path,
                  func, *args, **kwargs)
        if quota_names:
            job.quota_names = quota_names
        job = queue.put(job)
        job.addCallbacks(success=job_success_callback,
                         failure=job_failure_callback)
        return job

    def queueJob(self, func, context, *args, **kwargs):
        queue = self.getQueues()['']
        return self.queueJobInQueue(queue, ('default',), func, context, *args, **kwargs)

    def _queueJobsInQueue(self, queue, quota_names, job_infos, serialize=True):
        portal = getUtility(ISiteRoot)
        portal_path = portal.getPhysicalPath()
        pm = getToolByName(portal, 'portal_membership')
        user = pm.getAuthenticatedMember()
        user_id = user.getId()
        uf_path = user.aq_parent.aq_parent.getPhysicalPath()
        scheduled = []
        for (func, context, args, kwargs) in job_infos:
            context_path = context.getPhysicalPath()
            job = Job(_executeAsUser, portal_path, context_path, user_id,
                      uf_path, func, *args, **kwargs)
            scheduled.append(job)
        if serialize:
            job = serial(*scheduled)
        else:
            job = parallel(*scheduled)
        if quota_names:
            job.quota_names = quota_names
        job = queue.put(job)
        job.addCallbacks(success=job_success_callback,
                         failure=job_failure_callback)
        return job

    def queueSerialJobsInQueue(self, queue, quota_names, *job_infos):
        return self._queueJobsInQueue(queue, quota_names, job_infos, serialize=True)

    def queueParallelJobsInQueue(self, queue, quota_names, *job_infos):
        return self._queueJobsInQueue(queue, quota_names, job_infos, serialize=False)

    def queueSerialJobs(self, *job_infos):
        queue = self.getQueues()['']
        return self.queueSerialJobsInQueue(queue, ('default',), *job_infos)

    def queueParallelJobs(self, *job_infos):
        queue = self.getQueues()['']
        return self.queueParallelJobsInQueue(queue, ('default',), *job_infos)
