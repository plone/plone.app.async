import logging
from zope.event import notify
from plone.app.async.interfaces import QueueReady

logger = logging.getLogger('plone.app.async')


def set_quota(queue, quota_name, size):
    """Create quota or modify existing."""
    if quota_name in queue.quotas:
        queue.quotas[quota_name].size = size
        logger.info("Configured quota %r in queue %r", quota_name, queue.name)
    else:
        queue.quotas.create(quota_name, size=size)
        logger.info("Quota %r added to queue %r", quota_name, queue.name)


def notifyQueueReady(event):
    """Subscriber for IDispatcherActivated."""
    queue = event.object.parent
    notify(QueueReady(queue))


def configureQueue(event):
    """Subscriber for IQueueReady."""
    queue = event.object
    set_quota(queue, 'default', size=1)
