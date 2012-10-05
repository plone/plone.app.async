import logging
import datetime
from zope.event import notify
from plone.app.async.interfaces import QueueReady

logger = logging.getLogger('plone.app.async')


def set_ping_intervals(dispatcher, ping_secs, ping_death_secs):
    """Set ping intervals."""
    dispatcher.ping_interval = datetime.timedelta(seconds=ping_secs)
    dispatcher.ping_death_interval = datetime.timedelta(
        seconds=ping_death_secs)
    logger.info('dispatcher ping intervals configured')


def set_quota(queue, quota_name, size):
    """Create quota or modify existing."""
    if quota_name in queue.quotas:
        queue.quotas[quota_name].size = size
        logger.info("quota %r configured in queue %r", quota_name, queue.name)
    else:
        queue.quotas.create(quota_name, size=size)
        logger.info("quota %r added to queue %r", quota_name, queue.name)


def configureDispatcher(event):
    """Subscriber for IDispatcherActivated."""
    dispatcher = event.object
    set_ping_intervals(dispatcher, 2 * 60, 5 * 60)


def notifyQueueReady(event):
    """Subscriber for IDispatcherActivated."""
    queue = event.object.parent
    notify(QueueReady(queue))


def configureQueue(event):
    """Subscriber for IQueueReady."""
    queue = event.object
    set_quota(queue, 'default', size=1)
