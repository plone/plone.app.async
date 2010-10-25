from zope.component import getUtility
from Products.PloneTestCase import PloneTestCase
from Products.Five.testbrowser import Browser
from plone.app.async.testing import AsyncSandbox, async_layer
from plone.app.async.interfaces import IAsyncService

PloneTestCase.setupPloneSite()


class AsyncTestCase(AsyncSandbox, PloneTestCase.PloneTestCase):
    """We use this base class for all the tests in this package.
    """
    layer = async_layer

    def afterSetUp(self):
        super(AsyncTestCase, self).afterSetUp()
        self.async = getUtility(IAsyncService)


class FunctionalAsyncTestCase(AsyncTestCase, PloneTestCase.Functional): # Make ZTC happy
    """For functional tests.
    """
    layer = async_layer

    def getCredentials(self):
        return '%s:%s' % (PloneTestCase.default_user,
            PloneTestCase.default_password)

    def getBrowser(self, loggedIn=True):
        """ instantiate and return a testbrowser for convenience """
        browser = Browser()
        if loggedIn:
            auth = 'Basic %s' % self.getCredentials()
            browser.addHeader('Authorization', auth)
        return browser
