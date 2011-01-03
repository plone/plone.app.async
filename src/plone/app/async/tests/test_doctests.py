import doctest
import re
from zope.testing import module
from zope.testing import renormalizing
from Testing import ZopeTestCase
from Products.PloneTestCase.setup import PLONE40
from plone.app.async.tests.base import FunctionalAsyncTestCase

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)


def setUp(test):
    module.setUp(test, 'plone.app.async.tests.fakemodule')


def tearDown(test):
    module.tearDown(test)


if PLONE40:
    checker = renormalizing.RENormalizing([
        (re.compile('<zc.twist.Failure AccessControl.unauthorized.Unauthorized>'),
                    "<zc.twist.Failure <class 'AccessControl.unauthorized.Unauthorized'>>"),
        (re.compile('<zc.twist.Failure exceptions.RuntimeError>'),
                    "<zc.twist.Failure <type 'exceptions.RuntimeError'>>"),
        (re.compile("\[42, 'exceptions.RuntimeError: FooBared'\]"),
                    """[42, "<type 'exceptions.RuntimeError'>: FooBared"]"""),
    ])
else:
    checker = None


def test_suite():
    suite = ZopeTestCase.FunctionalDocFileSuite(
                'README.txt', package='plone.app.async',
                test_class=FunctionalAsyncTestCase,
                setUp=setUp, tearDown=tearDown,
                optionflags=optionflags,
                checker=checker)
    return suite
