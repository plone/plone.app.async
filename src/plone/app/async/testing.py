import time
import transaction
import uuid
from zope import component
from zope.app.appsetup.interfaces import DatabaseOpened
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from zc.async import dispatcher
from zc.async.subscribers import multidb_queue_installer
from zc.async.subscribers import ThreadedDispatcherInstaller
from zc.async.subscribers import agent_installer
from zc.async.interfaces import IDispatcherActivated
from zc.async.testing import tear_down_dispatcher
from plone.app.async.interfaces import IAsyncDatabase, IQueueReady
from plone.app.async.subscribers import notifyQueueReady, configureQueue
from plone.testing import z2
from plone.testing import Layer
from plone.testing import zodb
from plone.app.testing import (
    PloneFixture,
    PloneSandboxLayer,
    IntegrationTesting as BIntegrationTesting,
    FunctionalTesting as BFunctionalTesting,
    PLONE_SITE_ID,
    TEST_USER_NAME,
    TEST_USER_ID,
    TEST_USER_ROLES,
    SITE_OWNER_NAME,
)
from plone.app.testing import setRoles
from plone.app.testing.selenium_layers import SELENIUM_FUNCTIONAL_TESTING as SELENIUM_TESTING
from plone.app.testing.helpers import (
    login,
    logout,
)

PLONE_MANAGER_NAME = 'Plone_manager'
PLONE_MANAGER_ID = 'plonemanager'
PLONE_MANAGER_PASSWORD = 'plonemanager'

_dispatcher_uuid = uuid.uuid1()


try:
    from zope.component.hooks import getSite, setSite
except ImportError:
    from zope.app.component.hooks import getSite, setSite

try:
    from Zope2.App import zcml
except ImportError:
    from Products.Five import zcml


def loadZCMLFile(config, package=None, execute=True):
    # Unset current site for Zope 2.13
    saved = getSite()
    setSite(None)
    try:
        zcml.load_config(config, package, execute)
    finally:
        setSite(saved)


def loadZCMLString(string):
    # Unset current site for Zope 2.13
    saved = getSite()
    setSite(None)
    try:
        zcml.load_string(string)
    finally:
        setSite(saved)


def setUpQueue(db):
    event = DatabaseOpened(db)
    multidb_queue_installer(event)


def setUpDispatcher(db, uuid=None):
    event = DatabaseOpened(db)
    ThreadedDispatcherInstaller(poll_interval=0.2, uuid=uuid)(event)
    time.sleep(0.1) # Allow the thread to start up


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
    async_db = DB(DemoStorage(name='async'), database_name = 'async')
    multi_db = DB(DemoStorage('AsyncLayerS', base=db.storage),
                  databases = {'async': async_db,})
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
    for l in layer_or_layers:
        if not l in ASYNC_LAYERS:
            ASYNC_LAYERS.append(l)

class AsyncLayer(PloneSandboxLayer):

    def setUpZope(self, app, configurationContext):
        #self._stuff = Zope2.bobo_application._stuff
        z2.installProduct(app, 'Products.PythonScripts')
        import plone.app.async
        self.loadZCML('configure.zcml', package=plone.app.async)
        import plone.app.async.tests
        zcml.load_config('view.zcml', plone.app.async.tests)

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

    def setUpPloneSite(self, portal):
        # Plone stuff. Workflows, portal content. Members folder, etc.
        self.applyProfile(portal, 'Products.CMFPlone:plone')
        self.applyProfile(portal, 'Products.CMFPlone:plone-content')

# compat !
AsyncSandbox = AsyncLayer

class LayerMixin(Layer):
    defaultBases = (AsyncLayer() ,)
    def testTearDown(self):
        self.loginAsPortalOwner()
        if 'test-folder' in self['portal'].objectIds():
            self['portal'].manage_delObjects('test-folder')
        self['portal'].portal_membership.deleteMembers([PLONE_MANAGER_NAME])
        self.setRoles()
        self.login()

    def testSetUp(self):
        if not self['portal']['acl_users'].getUser(PLONE_MANAGER_NAME):
            self.loginAsPortalOwner()
            self.add_user(
                self['portal'],
                PLONE_MANAGER_ID,
                PLONE_MANAGER_NAME,
                PLONE_MANAGER_PASSWORD,
                ['Manager']+TEST_USER_ROLES)
            self.logout()
        self.login(TEST_USER_NAME)
        self.setRoles(['Manager'])
        if not 'test-folder' in self['portal'].objectIds():
            self['portal'].invokeFactory('Folder', 'test-folder')
        self['test-folder'] = self['folder'] = self['portal']['test-folder']
        self.setRoles(TEST_USER_ROLES)

    def add_user(self, portal, id, username, password, roles=None):
        if not roles: roles = TEST_USER_ROLES[:]
        self.loginAsPortalOwner()
        pas = portal['acl_users']
        pas.source_users.addUser(id, username, password)
        self.setRoles(roles, id)
        self.logout()

    def setRoles(self, roles=None, id=TEST_USER_ID):
        if roles is None:
            roles = TEST_USER_ROLES
        setRoles(self['portal'], id, roles)

    def loginAsPortalOwner(self):
        self.login(SITE_OWNER_NAME)

    def logout(self):
        logout()

    def login(self, id=None):
        if not id:
            id = TEST_USER_NAME
        try:
            z2.login(self['app']['acl_users'], id)
        except:
            z2.login(self['portal']['acl_users'], id)


class IntegrationTesting(LayerMixin, BIntegrationTesting,):
    def testSetUp(self):
        BIntegrationTesting.testSetUp(self)
        LayerMixin.testSetUp(self)


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
            Zope2.app(), environ=environ)
        request = app.REQUEST
        request['PARENTS'] = [app]
        # Make sure we have a zope.globalrequest request
        try:
            from zope.globalrequest import setRequest
            setRequest(request)
        except ImportError:
            pass
        self['app'] = app
        self['request'] = request
        self['portal'] = portal = self['app'][PLONE_SITE_ID]
        self.setUpEnvironment(portal)
        LayerMixin.testSetUp(self)

    def testTearDown(self):
        LayerMixin.testTearDown(self)
        # Make sure we have a zope.globalrequest request
        try:
            from zope.globalrequest import setRequest
            setRequest(None)
        except ImportError:
            pass
        # Close the database connection and the request
        app = self['app']
        app.REQUEST.close()
        del self['portal']
        del self['app']
        del self['request']

AsyncFunctionalTesting = FunctionalTesting # compat

PLONE_APP_ASYNC_FIXTURE             = AsyncLayer()
PLONE_APP_ASYNC_INTEGRATION_TESTING = IntegrationTesting(name = "PloneAppAsync:Integration")
PLONE_APP_ASYNC_FUNCTIONAL_TESTING  = AsyncFunctionalTesting( name = "PloneAppAsync:Functional")
PLONE_APP_ASYNC_SELENIUM_TESTING    = AsyncFunctionalTesting(bases = (SELENIUM_TESTING, PLONE_APP_ASYNC_FUNCTIONAL_TESTING,), name = "PloneAppAsync:Selenium")

"""
For plone.app.async descendants addons, you ll need to
also call setUpAsyncStorage with your layers if you
inherit from async layers
"""
registerAsyncLayers(
    [PLONE_APP_ASYNC_FIXTURE,
     PLONE_APP_ASYNC_INTEGRATION_TESTING,
     PLONE_APP_ASYNC_FUNCTIONAL_TESTING,
     PLONE_APP_ASYNC_SELENIUM_TESTING,]
)
