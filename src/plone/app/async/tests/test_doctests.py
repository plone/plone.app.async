# -*- coding: utf-8 -*-
from plone.app.async.testing import PLONE_APP_ASYNC_FUNCTIONAL_TESTING
from plone.app.async.tests import funcs
from plone.testing import layered

import doctest
import os
import unittest as unittest


optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)


def test_suite():
    """."""
    readme = os.path.join(os.path.dirname(__file__), '..', 'README.rst')
    suite = unittest.TestSuite()
    globs = {
        'createDocument': funcs.createDocument,
        'submitObject': funcs.submitObject,
    }
    suite.addTests([
        layered(
            doctest.DocFileSuite(
                readme,
                globs=globs,
                module_relative=False,
                optionflags=optionflags,
            ),
            layer=PLONE_APP_ASYNC_FUNCTIONAL_TESTING
        )
    ])
    return suite
