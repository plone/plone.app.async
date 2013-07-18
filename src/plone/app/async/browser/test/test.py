import inspect
from DateTime import DateTime
from datetime import datetime
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.component import getUtility
from Products.Five import BrowserView
from zc.async.interfaces import ACTIVE, COMPLETED
from zc.async.utils import custom_repr
from zc.twist import Failure
from plone.app.async.interfaces import IAsyncService
from webdav.xmltools import escape
from ZODB.utils import p64, u64
import simplejson as json
import pytz
from zope.component.hooks import getSite


from plone.app.async.interfaces import IAsyncService

def async_create(context):
    # context might be anywhere, need to create content at portal root
    site = getSite()
    context.invokeFactory('Folder', 'some_id') # <- AttributeError: 'NoneType' object has no attribute 'id'

class Test(BrowserView):

    def __call__(self):
        context = self.context
        async = getUtility(IAsyncService)
        import pdb;pdb.set_trace()  ## Breakpoint ##
        async.queueJob(async_create, context)

        


"""plone.app.async patch to provide old school Zope2 REQUEST on context.

Contributions:
    * Jean Jordaan
    * Robert Niederreiter
"""

import Zope2
import sys
from AccessControl.SecurityManagement import (
    noSecurityManager,
    newSecurityManager,
)
from zExceptions import BadRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest
from zope.component.hooks import setSite
from plone.app.async import service


def _executeAsUser(context_path, portal_path, uf_path,
                   user_id, func, *args, **kwargs):
    """Reconstruct environment and execute func.
    """
    transaction = Zope2.zpublisher_transactions_manager # Supports isDoomed
    transaction.begin()
    app = Zope2.app()
    result = None
    try:
        try:
            portal = app.unrestrictedTraverse(portal_path, None)
            if portal is None:
                raise BadRequest(
                    'Portal path %s not found' % '/'.join(portal_path))
            setSite(portal)

            if uf_path:
                acl_users = app.unrestrictedTraverse(uf_path, None)
                if acl_users is None:
                    raise BadRequest(
                        'Userfolder path %s not found' % '/'.join(uf_path))
                user = acl_users.getUserById(user_id)
                if user is None:
                    raise BadRequest('User %s not found' % user_id)
                newSecurityManager(None, user)

            context = portal.unrestrictedTraverse(context_path, None)
            if context is None:
                raise BadRequest(
                    'Context path %s not found' % '/'.join(context_path))

            # Create a request to work with
            response = HTTPResponse(stdout=sys.stdout)
            env = {'SERVER_NAME':'fake_server',
                   'SERVER_PORT':'80',
                   'REQUEST_METHOD':'GET'}
            request = HTTPRequest(sys.stdin, env, response)

            # Set values from original request
            original_request = kwargs.get('original_request')
            if original_request:
                for k,v in original_request.items():
                    request.set(k, v)
            context.REQUEST = request

            result = func(context, *args, **kwargs)

            # Avoid "can't pickle file objects"
            del context.REQUEST

            transaction.commit()
        except:
            transaction.abort()
            raise
    finally:
        noSecurityManager()
        setSite(None)
        app._p_jar.close()
    return result

service._executeAsUser = _executeAsUser        
