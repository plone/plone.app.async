===============
plone.app.async
===============

Introduction
============
Integration package for `zc.async`_ allowing asynchronous operations in
Plone 3 and 4.

Installation
============
You will typically run plone.app.async in a ZEO environment, where you
will have one or more *worker* instances that act as dispatchers carrying out
jobs queued by your main zope instances.

For the sake of simplicity it is assumed that you have one instance that can
queue new jobs, and one worker instance that consumes them, both operating on
a single database. In this case your buildout configuration will look similar
to::

  [zeo]
  recipe = plone.recipe.zope2zeoserver
  file-storage = ${buildout:directory}/var/filestorage/Data.fs

  [instance]
  recipe = plone.recipe.zope2instance
  eggs = Plone plone.app.async
  zcml =
  zcml-additional =
      <include package="plone.app.async" file="single_db_instance.zcml" />
  environment-vars =
      ZC_ASYNC_UUID ${buildout:directory}/var/instance-uuid.txt

  [worker]
  recipe = plone.recipe.zope2instance
  eggs = ${instance:eggs}
  zcml = ${instance:zcml}
  zcml-additional =
      <include package="plone.app.async" file="single_db_worker.zcml" />
  environment-vars =
      ZC_ASYNC_UUID ${buildout:directory}/var/worker-uuid.txt

There are two important stanzas here:

* Each instance has to set the ``ZC_ASYNC_UUID`` environment variable in order
  to integrate properly with zc.async.

* Each instance loads the ``single_db_instance.zcml`` configuration.
  The worker instance loads the ``single_db_worker.zcml`` configuration
  in order to setup the queue and configure itself as a dispatcher.

For more details please look at the `example buildout configurations`_ included in
the package.

.. _`example buildout configurations`: http://dev.plone.org/plone/browser/plone.app.async/trunk


Plone 3
-------

Use zope.app.keyreference


Plone 4
-------

Use five.intid


Credits
=======
Code from Enfold's `plone.async.core`_ package has been used for setting up the queues.

References
==========
* `zc.async`_ on PyPI
* `plone.async.core`_ Subversion repository

.. _zc.async: http://pypi.python.org/pypi/zc.async
.. _plone.async.core: https://svn.enfoldsystems.com/public/plone.async.core

