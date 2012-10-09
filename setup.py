from setuptools import setup, find_packages
from os.path import join

version = '1.6'

setup(name='plone.app.async',
      version=version,
      description="Integration package for zc.async allowing asynchronous operations in Plone",
      long_description=open("README.rst").read() + "\n" +
          open(join("src", "plone", "app", "async", "README.rst")).read() + "\n" +
          open(join("docs", "HISTORY.txt")).read(),
      classifiers=[
          'Environment :: Web Environment',
          'Framework :: Plone',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
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
          'setuptools',
          'zc.async',
          'zc.monitor',
          'zc.z3monitor',
          'five.intid >= 1.0.3',
          'zope.keyreference',
          'rwproperty',
          'simplejson',
      ],
      extras_require={'plone4_test': [
        'five.intid',
        'plone.app.testing',
      ]},
      entry_points={
          'z3c.autoinclude.plugin': 'target=plone',
      },
)
