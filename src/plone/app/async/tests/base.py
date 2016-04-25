# -*- coding: utf-8 -*-
from plone.app.async.interfaces import IAsyncService
from plone.app.async.testing import PLONE_APP_ASYNC_FIXTURE
from plone.app.async.testing import PLONE_APP_ASYNC_FUNCTIONAL_TESTING
from plone.app.async.testing import PLONE_APP_ASYNC_INTEGRATION_TESTING
from plone.app.async.testing import PLONE_APP_ASYNC_SELENIUM_TESTING
from plone.app.async.testing import PLONE_MANAGER_NAME
from plone.app.async.testing import PLONE_MANAGER_PASSWORD
from plone.app.async.testing import TEST_USER_ID
from plone.app.async.testing import TEST_USER_NAME
from plone.app.async.testing import TEST_USER_ROLES
from plone.app.testing import setRoles
from plone.testing.z2 import Browser
from zope.component import getUtility

import unittest2 as unittest


class AsyncTestCase(unittest.TestCase):
    """We use this base class for all the tests in this package.
    """
    layer = PLONE_APP_ASYNC_INTEGRATION_TESTING

    def setUp(self):
        super(AsyncTestCase, self).setUp()
        self.async = getUtility(IAsyncService)
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.folder = self.layer['test-folder']

    def tearDown(self):
        self.setRoles()

    def logout(self):
        self.layer.logout()

    def login(self, id=None):
        return self.layer.login(id)

    def setRoles(self, roles=None):
        self.layer.setRoles(roles)

class FunctionalAsyncTestCase(AsyncTestCase):
    """For functional tests.
    """
    layer = PLONE_APP_ASYNC_FUNCTIONAL_TESTING

    def getCredentials(self):
        return '%s:%s' % (
            PLONE_MANAGER_NAME,
            PLONE_MANAGER_PASSWORD)

    def getBrowser(self, loggedIn=True):
        """instantiate and return a testbrowser for convenience """
        browser = Browser(self.app)
        if loggedIn:
            auth = 'Basic %s' % self.getCredentials()
            browser.addHeader('Authorization', auth)
        return browser
