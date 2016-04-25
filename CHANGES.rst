Changelog
=========


1.7 (unreleased)
----------------

- Add zope.minmax dependency
  [vangheem]


1.4 (2012-10-09)
----------------
- fix tests, and helpers mainly for plone.app.async testing layer consumers (collective.cron) [kiorky]
- fix rst markup [kiorky]

1.3 (2012-10-05)
----------------

- buildout infrastructure refresh [kiorky]
- plone 4.3 compatibility [kiorky]
- Switch tests from collective.testcaselayer to plone.app.testing [kiorky]
- Merge expemimental work on UI & jobs back to master
  [kiorky]
- Add plone UI to view jobs
  [davisagli]
- Added support for queued/deferred tasks.
  [kiork,davisagli,do3cc]


1.2 - 2012-04-26
----------------

- Fix includes to work correctly with dexterity and
  to include simplejson.
  [vangheem]

- Change ping intervals to something more sane so it doesn't
  take so long for your workers to come back online after restart.
  [vangheem]


1.1 - 2011-07-21
----------------

- Add MANIFEST.in.
  [WouterVH]

- Change zcml:condition for zope.(app.)keyreference to use the plone-4
  feature.
  [vangheem]

- Always use loadZCMLFile in testcase layers to not break under Zope 2.13.
  [stefan]

- Avoid excessive ZODB growth by increasing the dispatcher ping intervals.
  https://mail.zope.org/pipermail/zope-dev/2011-June/043146.html
  [stefan]


1.0 - 2011-01-03
----------------

- Conditionally include zope.app.keyreference ZCML.
  [vangheem]

- Fix for async jobs started by anonymous user.
  [naro]

- Add full set of example buildouts.
  [stefan]

- Make tests pass under Plone 3 and 4. Exception representations have changed
  for some odd reason.
  [stefan]


1.0a6 - 2010-10-14
------------------

- First public release.
  [ggozad]


1.0a5 - 2010-10-14
------------------

- Instead of guessing where a userid may be coming from, record the path
  of the userfolder and use that to reinstate the user.
  [mj]


1.0a4 - 2010-09-09
------------------

- Use multi-db setup in tests to keep testcaselayer working as expected.
  [stefan, ggozad]


1.0a3 - 2010-09-01
------------------

- Separate helper function from test setup so it can be used in non-test code.
  [witsch]


1.0a2 - 2010-08-30
------------------

- Made separate zcml configurations for single/multi and instance/worker.
  [stefan, ggozad]


1.0a1 - 2010-08-25
------------------

- zc.async integration for Plone. Initial release.
  [ggozad, stefan]
