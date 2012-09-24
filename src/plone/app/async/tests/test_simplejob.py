import datetime
import pytz
import transaction
from zope.component import getUtility
from zc.async.testing import wait_for_result
from Products.PloneTestCase.PloneTestCase import default_user
from Products.CMFCore.utils import getToolByName
from plone.app.async.tests.base import AsyncTestCase
from plone.app.async.interfaces import IAsyncService
from plone.app.async.service import makeJob


def addNumbers(context, x1, x2):
    return x1+x2


def createDocument(context, anid, title, description, body):
    context.invokeFactory('Document', anid,
        title=title, description=description, text=body)
    return context[anid].id


def publishDocument(context, doc_id):
    doc = context[doc_id]
    wt = getToolByName(context, 'portal_workflow')
    wt.doActionFor(doc, 'submit')
    return "workflow_change"


def createDocumentAndPublish(context, anid, title, description, body):
    async = getUtility(IAsyncService)
    createDocument(context, anid, title, description, body)
    transaction.commit()
    # Get the local queue
    import zc.async
    queue = zc.async.local.getQueue()
    # Must not use a quota here!
    job = async.queueJobInQueue(queue, (), publishDocument, context, anid)
    return job


def reindexDocument(context):
    context.reindexObject()

def searchForDocument(context, doc_id):
    ct = getToolByName(context, 'portal_catalog')
    return len(ct.searchResults(getId = doc_id))


class TestSimpleJob(AsyncTestCase):
    """
    """
    def setUp(self):
        AsyncTestCase.setUp(self)
        self.login()
        self.setRoles(['Manager'])

    def test_add_job(self):
        """Tests adding a computational job and getting the result.
        """
        context = self.folder
        job = self.async.queueJob(addNumbers, context, 40, 2)
        transaction.commit()
        self.assertEqual(job.status, u'pending-status')
        wait_for_result(job)
        self.assertEqual(job.status, u'completed-status')
        self.assertEqual(job.result, 42)

    def test_add_persistent(self):
        """Adding a job that creates persistent objects.
        """
        job = self.async.queueJob(createDocument,
            self.folder, 'anide', 'atitle', 'adescr', 'abody')
        transaction.commit()
        self.assertEqual(job.status, u'pending-status')
        wait_for_result(job)
        self.assertEqual(job.status, u'completed-status')
        self.assertEqual(job.result, 'anide')
        self.failUnless('anide' in self.folder.objectIds())
        document = self.folder['anide']
        self.assertEqual(document.Creator(), default_user)

    def test_serial_jobs(self):
        """Queue two jobs the one after the other.
        """
        job1 = (createDocument, self.folder, ('anid2', 'atitle', 'adescr', 'abody'), {})
        job2 = (publishDocument, self.folder, ('anid2',), {})
        job = self.async.queueSerialJobs(job1,job2)
        transaction.commit()
        wait_for_result(job)
        self.assertEqual(job.result[0].result, 'anid2')
        self.assertEqual(job.result[1].result, 'workflow_change')
        doc = self.folder['anid2']
        wt = getToolByName(self.folder, 'portal_workflow')
        self.assertEqual(wt.getInfoFor(doc, 'review_state'), 'pending')

    def test_serial_jobs2(self):
        """Queue a job that queues another job.
        """
        job = self.async.queueJob(createDocumentAndPublish,
            self.folder, 'anid23', 'atitle', 'adescr', 'abody')
        transaction.commit()
        wait_for_result(job)
        self.assertEqual(job.result, 'workflow_change')
        doc = self.folder['anid23']
        wt = getToolByName(self.folder, 'portal_workflow')
        self.assertEqual(wt.getInfoFor(doc, 'review_state'), 'pending')

    def test_serial_jobs3(self):
        """Mix queueJob and queueSerialJobs.
        """
        job = self.async.queueJob(createDocument, self.folder, 'anid3', 'atitle', 'adescr', 'abody')
        self.assertEqual(job.quota_names, ('default',))

        job2 = self.async.queueSerialJobs(
            makeJob(publishDocument, self.folder, 'anid3'),
            makeJob(createDocument, self.folder, 'anotherid3', 'atitle', 'adescr', 'abody'),
        )
        self.assertEqual(job2.quota_names, ('default',))

        job3 = self.async.queueJob(publishDocument, self.folder, 'anotherid3')
        self.assertEqual(job3.quota_names, ('default',))
        transaction.commit()
        wait_for_result(job3)

        self.assertEqual(job.result, 'anid3')
        self.assertEqual(job2.result[0].result, 'workflow_change')
        self.assertEqual(job2.result[1].result, 'anotherid3')
        self.assertEqual(job3.result, 'workflow_change')

        wt = getToolByName(self.folder, 'portal_workflow')
        doc = self.folder['anid3']
        self.assertEqual(wt.getInfoFor(doc, 'review_state'), 'pending')
        doc = self.folder['anotherid3']
        self.assertEqual(wt.getInfoFor(doc, 'review_state'), 'pending')

    def test_indexing(self):
        """Queue indexing.
        """
        self.folder.invokeFactory('Document', 'anid4',
            title='Foo', description='Foo', text='foo')
        doc = self.folder['anid4']
        doc.setDescription('bar')
        ct = getToolByName(self.folder, 'portal_catalog')
        res = ct.searchResults(Description='bar')
        self.assertEqual(len(res), 0)

        job = self.async.queueJob(reindexDocument, doc)
        transaction.commit()
        wait_for_result(job)
        res = ct.searchResults(Description='bar')
        self.assertEqual(len(res), 1)

        """Demonstrate calling an object's method.
        """
        self.folder.invokeFactory('Document', 'anid5',
            title='Foo', description='Foo', text='foo')
        doc = self.folder['anid5']
        doc.setDescription('bar')
        ct = getToolByName(self.folder, 'portal_catalog')
        res = ct.searchResults(Description='bar')
        self.assertEqual(len(res), 1)

        job = self.async.queueJob(doc.__class__.reindexObject, doc)
        transaction.commit()
        wait_for_result(job)
        res = ct.searchResults(Description='bar')
        self.assertEqual(len(res), 2)

    def test_job_as_anonymous(self):
        # Add new document
        self.folder.invokeFactory('Document', 'anid6',
            title='Foo', description='Foo', text='foo')
        doc = self.folder['anid6']
        wt = getToolByName(self.folder, 'portal_workflow')
        # Document must be private (not accessible by anon)
        self.failUnless(wt.getInfoFor(doc, 'review_state') == 'private')

        job = self.async.queueJob(searchForDocument, doc, doc.getId())
        transaction.commit()
        # ok, owner can search for it
        self.assertEqual(wait_for_result(job), 1)

        # Let's try as anoymous
        self.logout()

        job = self.async.queueJob(searchForDocument, doc, doc.getId())
        transaction.commit()
        # not accessible by anon
        self.assertEqual(wait_for_result(job), 0)

    def test_job_with_delay(self):
        before = datetime.datetime.now(pytz.UTC)
        job = self.async.queueJobWithDelay(
            None, before + datetime.timedelta(seconds=1),
            searchForDocument, self.folder, self.folder.getId())
        transaction.commit()
        wait_for_result(job)
        after = datetime.datetime.now(pytz.UTC)
        self.assertTrue((after - before).seconds >= 1)


        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSimpleJob))
    return suite
