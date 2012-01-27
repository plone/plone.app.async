import rwproperty
import threading
import types
import zc.async.job
import Zope2
from AccessControl.SecurityManagement import noSecurityManager,\
    newSecurityManager, getSecurityManager
from AccessControl.User import SpecialUser
from zope.site.hooks import getSite, setSite
from Products.CMFCore.utils import getToolByName
from OFS.interfaces import ITraversable


tldata = threading.local()


class Job(zc.async.job.Job):
    # A job to be run in a Zope 2 context.
    # Stores the current site and user when the job is created,
    # and sets them back up while the job is run.

    portal_path = None
    uf_path = None
    user_id = None

    _callable_path = None

    @property
    def callable(self):
        if self._callable_path is not None:
            path = self._callable_path
            callable_root = tldata.app.unrestrictedTraverse(path)
            return getattr(callable_root, self._callable_name)
        return super(Job, self).callable
    @rwproperty.setproperty
    def callable(self, value):
        if isinstance(value, types.MethodType) and ITraversable.providedBy(value.im_self):
            self._callable_path = value.im_self.getPhysicalPath()
            self._callable_name = value.__name__
        else:
            zc.async.job.Job.callable.fset(self, value)

    def __init__(self, *args, **kwargs):
        super(Job, self).__init__(*args, **kwargs)

        portal = getToolByName(getSite(), 'portal_url').getPortalObject()
        self.portal_path = portal.getPhysicalPath()

        user = getSecurityManager().getUser()
        if isinstance(user, SpecialUser):
            self.uf_path, user_id = (), None
        else:
            self.uf_path = user.aq_parent.getPhysicalPath()
            self.user_id = user.getId()

    def setUp(self):
        db_name = Zope2.bobo_application._stuff[0].database_name
        tldata.app = app = Zope2.app(self._p_jar.get_connection(db_name))

        portal = app.unrestrictedTraverse(self.portal_path, None)
        old_site = getSite()
        setSite(portal)

        if self.uf_path:
            acl_users = app.unrestrictedTraverse(self.uf_path, None)
            user = acl_users.getUserById(self.user_id)
            newSecurityManager(None, user)

        return old_site

    def tearDown(self, setup_info):
        del tldata.app
        noSecurityManager()
        setSite(setup_info)
