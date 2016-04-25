# -*- coding: utf-8 -*-
from plone.app.async.tests.base import AsyncTestCase
from zc.async.testing import wait_for_result

import transaction


results = []


def job1(context):
    cid = context.invokeFactory('Document', '1',
                                title='Foo', description='Foo', text='Foo')
    results.append(1)
    return cid


def job_success_callback(result):
    results.append("Success: %s" % result)


def job_failure_callback(result):
    results.append("Failure")


class TestCallbacks(AsyncTestCase):

    def test_callback(self):
        self.layer.login_as_manager()
        results[:] = []
        job = self.async.queueJob(job1, self.folder)
        job.addCallback(job_success_callback)
        transaction.commit()
        wait_for_result(job)
        self.assertEqual(results, [1, "Success: 1"])

        results[:] = []
        job = self.async.queueJob(job1, self.folder)
        job.addCallbacks(failure=job_failure_callback)
        job.addCallbacks(success=job_success_callback)
        transaction.commit()
        wait_for_result(job)
        self.assertEquals(results, ["Failure"])
        failure = job.result
        exception = failure.value
        self.assertEqual(
            str(exception),
            'The id "1" is invalid - it is already in use.'
        )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCallbacks))
    return suite
