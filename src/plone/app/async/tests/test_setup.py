import transaction
from zope.component import getUtility, queryUtility
from Products.PloneTestCase import ptc
from zc.async import dispatcher
from zc.async.testing import wait_for_result
from plone.app.async.interfaces import IAsyncDatabase, IAsyncService
from plone.app.async.testing import _dispatcher_uuid, async_layer
from plone.app.async.tests.base import AsyncTestCase


def dbUsed(context):
    return str(context._p_jar.db())


class TestCaseSetup(AsyncTestCase):

    def test_async_db(self):
        self.failIfEqual(queryUtility(IAsyncDatabase), None)

    def test_dispatcher_present(self):
        self.failUnless(dispatcher.get() is not None)

    def test_queues_present(self):
        self.failUnless(self.async.getQueues() is not None)

    def test_quotas_present(self):
        self.failUnless(self.async.getQueues()[''].quotas.get('default') is not None)

    def test_job_sees_main_db(self):
        job = self.async.queueJob(dbUsed, self.folder)
        transaction.commit()
        wait_for_result(job)
        self.assertEqual(job.result, str(self.app._p_jar.db()))


class TestLayerSetup(ptc.PloneTestCase):

    layer = async_layer

    def afterSetUp(self):
        self.async = getUtility(IAsyncService)

    def test_async_db(self):
        self.failIfEqual(queryUtility(IAsyncDatabase), None)

    def test_dispatcher_present(self):
        self.failUnless(dispatcher.get(_dispatcher_uuid) is not None)

    def test_queues_present(self):
        self.failUnless(self.async.getQueues() is not None)

    def test_quotas_present(self):
        self.failUnless(self.async.getQueues()[''].quotas.get('default') is not None)

    def test_job_sees_main_db(self):
        job = self.async.queueJob(dbUsed, self.folder)
        transaction.commit()
        wait_for_result(job)
        self.assertEqual(job.result, str(self.app._p_jar.db()))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCaseSetup))
    suite.addTest(makeSuite(TestLayerSetup))
    return suite
