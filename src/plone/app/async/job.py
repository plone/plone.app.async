import threading
import zc.async.job
import Zope2
from AccessControl.SecurityManagement import noSecurityManager,\
    newSecurityManager, getSecurityManager
from AccessControl.User import SpecialUser
from zope.site.hooks import getSite, setSite
from Products.CMFCore.utils import getToolByName


tldata = threading.local()


class Job(zc.async.job.Job):
    # A job to be run in a Zope 2 context.
    # Stores the current site and user when the job is created,
    # and sets them back up while the job is run.

    portal_path = None
    uf_path = None
    user_id = None

    context_path = None
    func_name = None

    def _bind_and_call(self, *args, **kw):
        im_self = tldata.app.unrestrictedTraverse(self.context_path)
        func = getattr(im_self, self.func_name)
        return func(*args, **kw)

    def __init__(self, *args, **kwargs):
        super(Job, self).__init__(*args, **kwargs)

        # Instance methods cannot be directly pickled, so instead
        # we store the context path and method name on the job
        # and reconstitute the method in _bind_and_call
        if hasattr(self.callable, 'im_self'):
            im_self = self.callable.im_self
            if hasattr(im_self, 'getPhysicalPath'):
                self.context_path = im_self.getPhysicalPath()
                self.func_name = self.callable.func_name
                self.callable = self._bind_and_call

        portal = getToolByName(getSite(), 'portal_url').getPortalObject()
        self.portal_path = portal.getPhysicalPath()

        user = getSecurityManager().getUser()
        if isinstance(user, SpecialUser):
            self.uf_path, user_id = (), None
        else:
            self.uf_path = user.aq_parent.getPhysicalPath()
            self.user_id = user.getId()

    def setUp(self):
        tldata.app = app = Zope2.app()

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
