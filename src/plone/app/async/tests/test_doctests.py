# -*- coding: utf-8 -*-
from plone.app.async.testing import PLONE_APP_ASYNC_FUNCTIONAL_TESTING
from plone.testing import layered

import doctest
import glob
import logging
import os
import unittest2 as unittest


optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

def test_suite():
    """."""
    logger = logging.getLogger('plone.app.async.tests')
    cwd = os.path.dirname(__file__)
    files = []
    try:
        files = glob.glob(os.path.join(cwd, '*txt'))
        files += glob.glob(os.path.join(cwd, '*rst'))
        files += glob.glob(os.path.join(
            os.path.dirname(cwd), '*txt'))
        files += glob.glob(os.path.join(
            os.path.dirname(cwd), '*rst'))
    except Exception,e:
        logger.warn('No doctests for collective.cron')
    suite = unittest.TestSuite()
    globs = globals()
    for s in files:
        suite.addTests([
            layered(
                doctest.DocFileSuite(
                    s, 
                    globs = globs,
                    module_relative=False,
                    optionflags=optionflags,         
                ),
                layer=PLONE_APP_ASYNC_FUNCTIONAL_TESTING
            ),
        ])
    return suite
