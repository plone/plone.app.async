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
    site.invokeFactory('Folder', 'some_id') # <- AttributeError: 'NoneType' object has no attribute 'id'

class Test(BrowserView):

    def __call__(self):
        context = self.context
        async = getUtility(IAsyncService)
        async.queueJob(async_create, context)
