import transaction
from zc.async.testing import wait_for_result
from plone.app.async.utils import wait_for_all_jobs
from plone.app.async.tests.base import AsyncTestCase
import time


results = []

def job1(context):
    time.sleep(3)
    results.append(1)


def job2(context):
    time.sleep(2)
    results.append(2)


def job3(context):
    results.append(3)


class TestTiming(AsyncTestCase):

    def test_timing_serial(self):
        """Tests whether the jobs are *really* performed serially.
        """
        results[:] = []
        j1 = (job1, self.folder, (), {})
        j2 = (job2, self.folder, (), {})
        j3 = (job3, self.folder, (), {})
        job = self.async.queueSerialJobs(j1,j2,j3)
        transaction.commit()
        wait_for_result(job, seconds=20)
        self.assertEquals(results, [1, 2, 3])

    def test_timing_parallel(self):
        """Tests whether the jobs are *really* performed in parallel.
        """
        results[:] = []
        j1 = (job1, self.folder, (), {})
        j2 = (job2, self.folder, (), {})
        j3 = (job3, self.folder, (), {})
        job = self.async.queueParallelJobs(j1,j2,j3)
        transaction.commit()
        wait_for_result(job, seconds=20)
        self.assertEquals(set(results), set([3, 2, 1]))

    def test_default_quota(self):
        """When adding using queueJob, the quota is set to 1 always.
        So, everything will be performed serialy.
        """
        results[:] = []
        self.async.queueJob(job1, self.folder)
        self.async.queueJob(job2, self.folder)
        j3 = self.async.queueJob(job3, self.folder)
        transaction.commit()
        wait_for_result(j3, seconds=20)
        self.assertEquals(results, [1, 2, 3])

    def test_non_default_quota(self):
        """If we set a quota with size 2, then job1,2 will start. 2 will
        finish, 3 will start and finish, and then 1 will finish.
        """
        results[:] = []
        queue = self.async.getQueues()['']
        queue.quotas.create('size2', size=2)
        j1 = self.async.queueJobInQueue(queue, ('size2',), job1, self.folder)
        j1.quota_names = ('size2',)
        j2 = self.async.queueJobInQueue(queue, ('size2',), job2, self.folder)
        j2.quota_names = ('size2',)
        j3 = self.async.queueJobInQueue(queue, ('size2',), job3, self.folder)
        j3.quota_names = ('size2',)
        transaction.commit()
        wait_for_result(j1, seconds=20)
        self.assertEquals(results, [2, 3, 1])

    def test_wait_for_all_jobs(self):
        """Tests if wait_for_all_jobs really works
        """
        results[:] = []
        self.async.queueJob(job1, self.folder)
        self.async.queueJob(job2, self.folder)
        self.async.queueJob(job3, self.folder)
        transaction.commit()
        wait_for_all_jobs()
        self.assertEquals(results, [1, 2, 3])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestTiming))
    return suite

