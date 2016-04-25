# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName


def addNumbers(context, x1, x2):
    return x1 + x2


def createDocument(context, id, title, description, body):
    context.invokeFactory('Document', id,
                          title=title, description=description, text=body)
    return context[id].id


def submitObject(context, id):
    obj = context[id]
    wt = getToolByName(context, 'portal_workflow')
    wt.doActionFor(obj, 'submit')


def failingJob(context):
    raise RuntimeError("FooBared")

results = []


def successHandler(event):
    results.append(event.object)


def failureHandler(event):
    exc = event.object
    results.append("%s: %s" % (exc.type, exc.value))


def job_failure_callback(result):
    results.append(result)


def job_success_callback(result):
    results.append("Success: %s" % result)
