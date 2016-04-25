# -*- coding: utf-8 -*-
from plone.app.async.interfaces import IAsyncService
from plone.app.async.tests.base import FunctionalAsyncTestCase
from plone.app.async.tests.funcs import createDocument
from plone.app.async.utils import wait_for_all_jobs
from zope.component import getUtility
from Products.Five.browser import BrowserView

TESTPAGE = """\
<html>
<body>
    <form action="{url:s}" method="post">
        <input type="submit" name="apply" value="Apply" />
    </form>
</body>
</html>
"""


class TestView(BrowserView):

    def __call__(self):
        if self.request.method == 'POST':
            self.testing()
            return ''
        self.request.RESPONSE.setHeader('Content-Type', 'text/html')
        return TESTPAGE.format(url=self.context.absolute_url() + '/@@testview')

    def testing(self):
        async = getUtility(IAsyncService)
        async.queueJob(
            createDocument,
            self.context,
            'anidf',
            'atitle',
            'adescr',
            'abody'
        )


class TestFunctional(FunctionalAsyncTestCase):
    """This test is here to make sure that the FunctionalAsyncTestCase is
    working properly. In order to do we register and load a browser view that
    adds a job.
    """

    def test_view(self):
        browser = self.getBrowser()
        browser.open(self.folder.absolute_url() + "/@@testview")
        browser.getControl("Apply").click()
        wait_for_all_jobs()
        self.failUnless('anidf' in self.folder)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFunctional))
    return suite
