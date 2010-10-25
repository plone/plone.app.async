import doctest
from zope.testing import module
from Testing import ZopeTestCase
from plone.app.async.tests.base import FunctionalAsyncTestCase

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)


def setUp(test):
    module.setUp(test, 'plone.app.async.tests.fakemodule')


def tearDown(test):
    module.tearDown(test)


def test_suite():
    suite = ZopeTestCase.FunctionalDocFileSuite(
            'README.txt', package='plone.app.async',
            test_class=FunctionalAsyncTestCase,
            setUp=setUp, tearDown=tearDown,
            optionflags=optionflags)
    return suite
