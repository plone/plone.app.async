# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup
from os.path import join


version = '1.7.0dev0'
description = 'Integration package for zc.async allowing asynchronous ' \
              'operations in Plone'

setup(
    name='plone.app.async',
    version=version,
    description=description,
    long_description=(
        open('README.rst').read() +
        '\n' +
        open(join("src", "plone", "app", "async", "README.rst")).read() +
        '\n' +
        open('CHANGES.rst').read()
    ),
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Plone',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Framework :: Plone :: 5.0"
    ],
    keywords='plone async asynchronous',
    author='Plone Foundation',
    author_email='plone-developers@lists.sourceforge.net',
    url='http://plone.org/products/plone.app.async',
    download_url='http://pypi.python.org/pypi/plone.app.async',
    license='GPL version 2',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['plone', 'plone.app'],
    include_package_data=True,
    platforms='Any',
    zip_safe=False,
    install_requires=[
        'Plone',
        'setuptools',
        'zc.async[monitor]',
        'zc.z3monitor',
        'zope.keyreference',
        'zope.minmax'
    ],
    extras_require={
        'test': [
            'plone.app.testing',
            'plone.app.contenttypes[test]'
        ]
    },
    entry_points={
        'z3c.autoinclude.plugin': 'target=plone',
    },
)
