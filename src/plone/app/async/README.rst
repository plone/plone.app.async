User Documentation
==================

Basic use
---------

Assuming your setup is done correctly, you can start by obtaining the
``AsyncService`` utility::

    >>> from zope.component import getUtility
    >>> from plone.app.async.interfaces import IAsyncService
    >>> async = getUtility(IAsyncService)
    >>> async
    <plone.app.async.service.AsyncService object at ...>
    >>> folder = layer['test-folder']
    >>> portal = layer['portal']

You can already get the ``zc.async`` queues::

    >>> async.getQueues()
    <zc.async.queue.Queues object at ...>

    >>> import zc.async.dispatcher
    >>> from plone.app.async.testing import _dispatcher_uuid
    >>> zc.async.dispatcher.get(_dispatcher_uuid)
    <zc.async.dispatcher.Dispatcher object at ...>
    >>> queue = async.getQueues()['']
    >>> queue
    <zc.async.queue.Queue object at ...>

Let's define a simple function to be executed asynchronously. Note that the
first argument **must** be a valid Zope object::

    >>> from plone.app.async.tests.funcs import *

and queue it::

    >>> job = async.queueJob(addNumbers, folder, 40, 2)
    >>> len(queue)
    1
    >>> job.status
    u'pending-status'


In real life the job would be executed by the worker. In the tests we need
to commit in order to let the  dispatcher become aware of the job and
execute it.  Also we wait for the job to complete before continuing with the
test::

    >>> import transaction
    >>> from zc.async.testing import wait_for_result
    >>> transaction.commit()
    >>> wait_for_result(job)
    42

Batches of jobs
----------------

Let's now try some jobs that create persistent objects. First define
the tasks to be executed asynchronously::

    >>> from Products.CMFCore.utils import getToolByName


Queue a job that creates a document and another that submits it::

    >>> job = async.queueJob(createDocument, folder,
    ...     'foo', 'title', 'description', 'body')
    >>> job2 = async.queueJob(submitObject, folder, 'foo')
    >>> transaction.commit()

Because by default the jobs are executed with the default quota set to 1,
(i.e. only one job can be executed at a time), jobs are executed serially and
according to the order by which they were submitted. Hence, waiting for the
job that submits the document implies that the one that created it has already 
been carried out::

    >>> wait_for_result(job2)
    >>> wt = getToolByName(folder, 'portal_workflow')
    >>> doc = folder['foo']
    >>> wt.getInfoFor(doc, 'review_state')
    'pending'

You can also queue a *batch* of jobs to be executed serially as one job by use
of ``queueSerialJobs``::

    >>> from plone.app.async.service import makeJob
    >>> job = async.queueSerialJobs(
    ...     makeJob(createDocument, folder,
    ...             'bar', 'title', 'description', 'body'),
    ...     makeJob(submitObject, folder, 'bar'))
    >>> transaction.commit()
    >>> res = wait_for_result(job)
    >>> res[0].result
    'bar'
    >>> res[1].status
    u'completed-status'
    >>> doc = folder['bar']
    >>> wt.getInfoFor(doc, 'review_state')
    'pending'

If you want to execute jobs in parallel, you can use ``queueParallelJobs``.

Security and user permissions
-----------------------------

When a job is queued by some user, it is also executed by the same user, with
the same roles and permissions. So for instance::

    >>> job = async.queueJob(createDocument, portal,
    ...     'foo', 'title', 'description', 'body')
    >>> transaction.commit()

will fail as the user is not allowed to create content in the Plone root::

    >>> wait_for_result(job)
    <...Unauthorized...

Handling failure and success
----------------------------

If you need to act on the result of a job or handle a failure you can do
so by adding callbacks. For instance::

    >>> from plone.app.async.tests import funcs
    >>> job = async.queueJob(addNumbers, folder, 40, 2)
    >>> c = job.addCallback(job_success_callback)
    >>> transaction.commit()
    >>> r = wait_for_result(job)
    >>> funcs.results
    ['Success: 42']

Failures can be handled in the same way::

    >>> job = async.queueJob(failingJob, folder)
    >>> c = job.addCallbacks(failure=job_failure_callback)
    >>> transaction.commit()
    >>> r = wait_for_result(job)
    >>> funcs.results
    [...RuntimeError...

It is also possible to handle all successful/failed jobs (for instance if you
want to send an email upon failure) by subscribing to the respective event::

    >>> from zope.component import provideHandler
    >>> from plone.app.async.interfaces import IJobSuccess, IJobFailure
    >>> provideHandler(successHandler, [IJobSuccess])
    >>> provideHandler(failureHandler, [IJobFailure])
    >>> funcs.results = []
    >>> job1 = async.queueJob(addNumbers, folder, 40, 2)
    >>> job2 = async.queueJob(failingJob, folder)
    >>> transaction.commit()
    >>> r = wait_for_result(job2)
    >>> funcs.results
    [42, ...RuntimeError...FooBared...

Let's clean up and unregister the success/failure handlers...::

    >>> from zope.component import getGlobalSiteManager
    >>> gsm = getGlobalSiteManager()
    >>> _ = gsm.unregisterHandler(successHandler, [IJobSuccess])
    >>> _ = gsm.unregisterHandler(failureHandler, [IJobFailure])
    >>> transaction.commit()

