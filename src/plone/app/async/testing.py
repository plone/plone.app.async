import time
import transaction
import Zope2
import uuid
from zope import component
from zope.app.appsetup.interfaces import DatabaseOpened
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from zc.async import dispatcher
from zc.async.subscribers import QueueInstaller
from zc.async.subscribers import ThreadedDispatcherInstaller
from zc.async.subscribers import agent_installer
from zc.async.interfaces import IDispatcherActivated
from zc.async.testing import tear_down_dispatcher
from Products.PloneTestCase import ptc
from collective.testcaselayer.ptc import BasePTCLayer, ptc_layer
from plone.app.async.interfaces import IAsyncDatabase, IQueueReady
from plone.app.async.subscribers import notifyQueueReady, configureQueue

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


_dispatcher_uuid = uuid.uuid1()
_async_layer_db = None


def createAsyncDB(main_db):
    async_db = DB(DemoStorage(), database_name='async')
    async_db.databases['unnamed'] = main_db # Fake dbtab
    main_db.databases['async'] = async_db   # Fake dbtab
    return async_db


def setUpQueue(db):
    event = DatabaseOpened(db)
    QueueInstaller()(event)


def setUpDispatcher(db, uuid=None):
    event = DatabaseOpened(db)
    ThreadedDispatcherInstaller(poll_interval=0.2, uuid=uuid)(event)
    time.sleep(0.1) # Allow the thread to start up


def cleanUpDispatcher(uuid=None):
    dispatcher_object = dispatcher.get(uuid)
    if dispatcher_object is not None:
        tear_down_dispatcher(dispatcher_object)
        dispatcher.pop(dispatcher_object.UUID)


class AsyncLayer(BasePTCLayer):

    def afterSetUp(self):
        global _async_layer_db
        import plone.app.async
        loadZCMLFile('configure.zcml', plone.app.async)
        main_db = self.app._p_jar.db()
        _async_layer_db = createAsyncDB(main_db)
        component.provideUtility(_async_layer_db, IAsyncDatabase)
        component.provideHandler(agent_installer, [IDispatcherActivated])
        component.provideHandler(notifyQueueReady, [IDispatcherActivated])
        component.provideHandler(configureQueue, [IQueueReady])
        setUpQueue(_async_layer_db)
        setUpDispatcher(_async_layer_db, _dispatcher_uuid)
        transaction.commit()

    def afterClear(self):
        global _async_layer_db
        cleanUpDispatcher(_dispatcher_uuid)
        gsm = component.getGlobalSiteManager()
        gsm.unregisterUtility(_async_layer_db, IAsyncDatabase)
        gsm.unregisterHandler(agent_installer, [IDispatcherActivated])
        gsm.unregisterHandler(notifyQueueReady, [IDispatcherActivated])
        gsm.unregisterHandler(configureQueue, [IQueueReady])
        _async_layer_db = None

async_layer = AsyncLayer(bases=[ptc_layer])


class AsyncSandbox(ptc.Sandboxed):

    def afterSetUp(self):
        main_db = self.app._p_jar.db()
        async_db = createAsyncDB(main_db)
        component.provideUtility(async_db, IAsyncDatabase)
        setUpQueue(async_db)
        setUpDispatcher(async_db)
        transaction.commit()
        self._stuff = Zope2.bobo_application._stuff
        Zope2.bobo_application._stuff = (main_db,) + self._stuff[1:]

    def afterClear(self):
        cleanUpDispatcher()
        component.provideUtility(_async_layer_db, IAsyncDatabase)
        if hasattr(self, '_stuff'):
            Zope2.bobo_application._stuff = self._stuff


# We want to make sure that testcaselayer can create new
# sandboxes at will:

def __init__(self, *args, **kw):
    DB._old_init(self, *args, **kw)
    if (_async_layer_db is not None and
        self.database_name == 'unnamed' and
        'async' not in self.databases):
        _async_layer_db.databases['unnamed'] = self # Fake dbtab
        self.databases['async'] = _async_layer_db   # Fake dbtab

DB._old_init = DB.__init__
DB.__init__ = __init__
