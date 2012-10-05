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


local_zone = DateTime().asdatetime().tzinfo


def get_failure(job):
    if job.status == COMPLETED and isinstance(job.result, Failure):
        return job.result
    elif job.status not in (ACTIVE, COMPLETED) and job._retry_policy \
            and job._retry_policy.data.get('job_error', 0):
        return job._retry_policy.data['last_job_error']


class JobsView(BrowserView):

    js = """
jQuery(function($) {
  var update = function() {
    var escape = function(s) {
        return s.replace('<', '&lt;').replace('>', '&gt;');
    }

    $.fn.render = function(data) {
      var rows = ['<tr><th>Job</th><th>Status</th></tr>'];
      $(data).each(function(i, job) {
        row = ['<tr><td><div><strong>' + escape(job.callable) +
            '</strong></div>'];
        row.push('<div>' + escape(job.args) + '</div></td>');
        row.push('<td>' + job.status);
        if (job.progress)
          row.push('<div>' + job.progress + '</div>');
        if (job.failure)
          row.push('<div>' + job.failure + '</div>')
        rows.push(row.join('') + '</tr>');
      });
      $('table', this).html(rows.join(''));
      var form = this.closest('form');
      var legend = $('legend', this);
      $('.formTab span', form).eq($('legend', form).
        index(legend)).html(legend.html().replace('0', data.length));
    };

    $.getJSON('jobs.json', function(data) {
      $('#queued-jobs').render(data.queued);
      $('#active-jobs').render(data.active);
      $('#dead-jobs').render(data.dead);
      $('#completed-jobs').render(data.completed);
    });

    setTimeout(update, 5000);
  };
  update();
});
"""


class JobsJSON(BrowserView):

    def _find_jobs(self):
        service = getUtility(IAsyncService)
        queue = service.getQueues()['']
        for job in queue:
            yield 'queued', job
        for da in queue.dispatchers.values():
            for agent in da.values():
                for job in agent:
                    yield 'active', job
                for job in agent.completed:
                    if isinstance(job.result, Failure):
                        yield 'dead', job
                    else:
                        yield 'completed', job

    def _filter_jobs(self):
        for job_status, job in self._find_jobs():
            job_context = job.args[0]
            if type(job_context) == tuple and \
                    job_context[:len(self.portal_path)] == self.portal_path:
                yield job_status, job

    @lazy_property
    def portal_path(self):
        return self.context.getPhysicalPath()

    @lazy_property
    def now(self):
        return datetime.now(pytz.UTC)

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/json')

        jobs = {
            'queued': [],
            'active': [],
            'completed': [],
            'dead': [],
        }

        for job_status, job in self._filter_jobs():
            jobs[job_status].append({
                'id': u64(job._p_oid),
                'callable': custom_repr(job.callable),
                'args': self.format_args(job),
                'status': self.format_status(job),
                'progress': self.format_progress(job),
                'failure': self.format_failure(job),
            })

        return json.dumps(jobs)

    def format_status(self, job):
        if job.status == COMPLETED:
            return 'Completed at %s' % self.format_datetime(job.active_end)
        elif job.status == ACTIVE:
            return 'Started at %s' % self.format_datetime(job.active_start)
        else:
            if job.begin_after > self.now:
                retries = 0
                if job._retry_policy:
                    retries = job._retry_policy.data.get('job_error', 0)
                if retries:
                    return 'Retry #%s scheduled for %s' % (retries,
                        self.format_datetime(job.begin_after))
                else:
                    return 'Scheduled for %s' % self.format_datetime(
                        job.begin_after)
            else:
                return 'Queued at %s' % self.format_datetime(job.begin_after)

    def format_progress(self, job):
        if job.status != ACTIVE:
            return ''

        progress = job.annotations.get('progress', 0.0) * 100
        if not progress:
            return ''

        return """<div style="width:100px; border: solid 1px #000;">
<div style="width:%dpx; background: red;">&nbsp;</div></div>%d%%""" % (
            progress, progress)

    def format_args(self, job):
        try:
            argnames = inspect.getargspec(job.callable).args
        except:
            argnames = None
        if argnames is not None:
            args = ', '.join('%s=%s' % (k, v)
                                for k, v in zip(argnames, job.args))
        else:
            args = ', '.join(custom_repr(a) for a in job.args)
        kwargs = ', '.join(k + "=" + custom_repr(v)
                            for k, v in job.kwargs.items())
        if args and kwargs:
            args += ", " + kwargs
        elif kwargs:
            args = kwargs
        return 'Args: %s' % args

    def format_failure(self, job):
        failure = get_failure(job)
        if failure is None:
            return ''

        res = '%s: %s' % (failure.type.__name__, failure.getErrorMessage())
        res += ' <a href="%s/manage-job-error?id=%s">Details</a>' % (
            self.context.absolute_url(), u64(job._p_oid))
        return res

    def format_datetime(self, dt):
        return dt.astimezone(local_zone).strftime('%I:%M:%S %p, %Y-%m-%d')


class TracebackView(BrowserView):

    def __call__(self, id):
        queue = getUtility(IAsyncService).getQueues()['']
        job = queue._p_jar.get(p64(int(id)))
        failure = get_failure(job)
        return escape(failure.getTraceback())
