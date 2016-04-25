# -*- coding: utf-8 -*-
from plone.app.async.interfaces import IAsyncDatabase
from plone.app.async.interfaces import IQueueReady
from plone.app.async.subscribers import configureQueue
from plone.app.async.subscribers import notifyQueueReady
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.testing import FunctionalTesting as BFunctionalTesting
from plone.app.testing import IntegrationTesting as BIntegrationTesting
from plone.app.testing import logout
from plone.app.testing import login
from plone.app.testing import PLONE_SITE_ID
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_ROLES
from plone.app.testing.selenium_layers import SELENIUM_FUNCTIONAL_TESTING as SELENIUM_TESTING  # noqa
from plone.testing import Layer
from plone.testing import z2
from plone.testing import zodb
from zc.async import dispatcher
from zc.async.interfaces import IDispatcherActivated
from zc.async.subscribers import agent_installer
from zc.async.subscribers import multidb_queue_installer
from zc.async.subscribers import ThreadedDispatcherInstaller
from zc.async.testing import tear_down_dispatcher
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from zope import component
from zope.globalrequest import setRequest
from zope.app.appsetup.interfaces import DatabaseOpened

import time
import transaction
import uuid


PLONE_MANAGER_NAME = 'Plone_manager'
PLONE_MANAGER_ID = 'plonemanager'
PLONE_MANAGER_PASSWORD = 'plonemanager'

_dispatcher_uuid = uuid.uuid1()


def setUpQueue(db):
    event = DatabaseOpened(db)
    multidb_queue_installer(event)


def setUpDispatcher(db, uuid=None):
    event = DatabaseOpened(db)
    ThreadedDispatcherInstaller(poll_interval=0.2, uuid=uuid)(event)
    time.sleep(0.1)  # Allow the thread to start up


def cleanUpDispatcher(uuid=None):
    dispatcher_object = dispatcher.get(uuid)
    if dispatcher_object is not None:
        tear_down_dispatcher(dispatcher_object)
        dispatcher.pop(dispatcher_object.UUID)

"""
    The very all Magical of this layer is here:

    Monkey patching stackDemoStorage to load our async mountpoint

"""
ASYNC_LAYERS = []
stackDemoStorage_attr = '_old_stackDemoStorage'


def async_stackDemoStorage(*args, **kwargs):
    db = getattr(zodb, stackDemoStorage_attr)(*args, **kwargs)
    # we patch only the last stacked storage.
    if db.storage.__name__ in [l.__name__ for l in ASYNC_LAYERS]:
        db = createAsyncDB(db)
    return db

if not getattr(zodb, stackDemoStorage_attr, None):
    setattr(zodb, stackDemoStorage_attr, zodb.stackDemoStorage)
    zodb.stackDemoStorage = async_stackDemoStorage


def createAsyncDB(db):
    async_db = DB(DemoStorage(name='async'), database_name='async')
    multi_db = DB(
        DemoStorage('AsyncLayerS', base=db.storage),
        databases={'async': async_db, }
    )
    component.provideUtility(async_db, IAsyncDatabase)
    component.provideHandler(agent_installer, [IDispatcherActivated])
    component.provideHandler(notifyQueueReady, [IDispatcherActivated])
    component.provideHandler(configureQueue, [IQueueReady])
    setUpQueue(multi_db)
    setUpDispatcher(multi_db, _dispatcher_uuid)
    transaction.commit()
    return multi_db


def registerAsyncLayers(layer_or_layers):
    """Third magic is there, you ll need in
    each plone.app.async layer to register
    yourself as beeing an async layer
    See the call at the end of the file
    """
    if not isinstance(layer_or_layers, list):
        layer_or_layers = [layer_or_layers]
    for ly in layer_or_layers:
        if ly not in ASYNC_LAYERS:
            ASYNC_LAYERS.append(ly)


class AsyncLayer(PloneSandboxLayer):

    defaultBases = (
        PLONE_APP_CONTENTTYPES_FIXTURE,
    )

    def setUpZope(self, app, configurationContext):
        # self._stuff = Zope2.bobo_application._stuff
        z2.installProduct(app, 'Products.PythonScripts')
        import plone.app.async
        self.loadZCML('configure.zcml', package=plone.app.async)
        import plone.app.async.tests
        self.loadZCML('view.zcml', package=plone.app.async.tests)

    def tearDown(self):
        """ Second magical thing to remember in this layer:
            Be sure not to have any transaction ongoing
            Unless that you ll have::

            ZODB.POSException.StorageTransactionError:
                Duplicate tpc_begin calls for same transaction
        """
        cleanUpDispatcher(_dispatcher_uuid)
        gsm = component.getGlobalSiteManager()
        gsm.unregisterHandler(agent_installer, [IDispatcherActivated])
        gsm.unregisterHandler(notifyQueueReady, [IDispatcherActivated])
        gsm.unregisterHandler(configureQueue, [IQueueReady])
        db = gsm.getUtility(IAsyncDatabase)
        gsm.unregisterUtility(db, IAsyncDatabase)
        transaction.commit()
        PloneSandboxLayer.tearDown(self)


class LayerMixin(Layer):
    defaultBases = (
        AsyncLayer(),
    )

    def testSetUp(self):
        self.login_as_manager()
        pas = self['portal']['acl_users']
        if not pas.getUser(PLONE_MANAGER_NAME):
            pas.source_users.addUser(
                PLONE_MANAGER_ID,
                PLONE_MANAGER_NAME,
                PLONE_MANAGER_PASSWORD
            )
            setRoles(
                self['portal'],
                PLONE_MANAGER_ID, ['Manager'] + TEST_USER_ROLES
            )

        if 'test-folder' not in self['portal'].objectIds():
            self['portal'].invokeFactory('Folder', 'test-folder')
        self['test-folder'] = self['folder'] = self['portal']['test-folder']
        self.logout_as_manager()
        transaction.commit()

    def testTearDown(self):
        self.login_as_manager()
        if 'test-folder' in self['portal'].objectIds():
            self['portal'].manage_delObjects('test-folder')
        self['portal'].portal_membership.deleteMembers([PLONE_MANAGER_NAME])
        self.logout_as_manager()
        transaction.commit()

    def login_as_manager(self):
        login(self['portal'], TEST_USER_NAME)
        setRoles(self['portal'], TEST_USER_ID, ['Manager'])

    def logout_as_manager(self):
        setRoles(self['portal'], TEST_USER_ID, TEST_USER_ROLES)
        logout()

    def login(self):
        login(self['portal'], TEST_USER_NAME)
        setRoles(self['portal'], TEST_USER_ID, TEST_USER_ROLES)

    def logout(self):
        logout()


class IntegrationTesting(LayerMixin, BIntegrationTesting,):

    def testSetUp(self):
        BIntegrationTesting.testSetUp(self)
        transaction.commit()
        LayerMixin.testSetUp(self)
        transaction.commit()


class FunctionalTesting(LayerMixin, BFunctionalTesting):

    def testSetUp(self):
        """Do not mess up here with another stacked
        demo storage!!!"""
        import Zope2
        environ = {
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': str(self['port']),
        }
        app = z2.addRequestContainer(
            Zope2.app(),
            environ=environ
        )
        request = app.REQUEST
        request['PARENTS'] = [app]
        setRequest(request)
        self['app'] = app
        self['request'] = request
        self['portal'] = portal = self['app'][PLONE_SITE_ID]
        transaction.commit()
        self.setUpEnvironment(portal)
        transaction.commit()
        LayerMixin.testSetUp(self)
        transaction.commit()

    def testTearDown(self):
        LayerMixin.testTearDown(self)
        # Make sure we have a zope.globalrequest request
        from zope.globalrequest import setRequest
        setRequest(None)
        # Close the database connection and the request
        app = self['app']
        app.REQUEST.close()
        del self['portal']
        del self['app']
        del self['request']

AsyncFunctionalTesting = FunctionalTesting  # compat

PLONE_APP_ASYNC_FIXTURE = AsyncLayer()
PLONE_APP_ASYNC_INTEGRATION_TESTING = IntegrationTesting(
    name="PloneAppAsync:Integration")
PLONE_APP_ASYNC_FUNCTIONAL_TESTING = AsyncFunctionalTesting(
    name="PloneAppAsync:Functional")
PLONE_APP_ASYNC_SELENIUM_TESTING = AsyncFunctionalTesting(
    bases=(SELENIUM_TESTING, PLONE_APP_ASYNC_FUNCTIONAL_TESTING, ),
    name="PloneAppAsync:Selenium"
)

"""
For plone.app.async descendants addons, you ll need to
also call setUpAsyncStorage with your layers if you
inherit from async layers
"""
registerAsyncLayers(
    [PLONE_APP_ASYNC_FIXTURE,
     PLONE_APP_ASYNC_INTEGRATION_TESTING,
     PLONE_APP_ASYNC_FUNCTIONAL_TESTING,
     PLONE_APP_ASYNC_SELENIUM_TESTING, ]
)
