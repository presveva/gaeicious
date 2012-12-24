#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
import datetime
from google.appengine.api import mail, app_identity
from google.appengine.ext import deferred, ndb
from models import Bookmarks, UserInfo


def dtf(value, format='%d/%m/%Y - %H:%M UTC'):
    return value.strftime(format)

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates', 'partials']))
jinja_environment.filters['dtf'] = dtf


def daily_digest(user):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.user == user)
    bmq = bmq.filter(Bookmarks.trashed == False)
    bmq = bmq.filter(Bookmarks.data > period)
    bmq = bmq.order(-Bookmarks.data)
    title = '(%s) Daily digest for your activity: %s' % (app_identity.get_application_id(), dtf(now))
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, user.email(), html, title, _target="worker", _queue="emails")


def feed_digest(feedk):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    feed = feedk.get()
    bmq = Bookmarks.query(Bookmarks.user == feed.user)
    bmq = bmq.filter(Bookmarks.feed == feed.key)
    bmq = bmq.filter(Bookmarks.trashed == False)
    bmq = bmq.filter(Bookmarks.data > period)
    bmq = bmq.order(-Bookmarks.data)
    title = '(%s) Daily digest for %s' % (app_identity.get_application_id(), feed.blog)
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest,
                       feed.user.email(),
                       html,
                       title,
                       _target="worker",
                       _queue="emails")
        ndb.delete_multi([bm.key for bm in bmq])


def send_bm(bmk):
    bm = bmk.get()
    message = mail.EmailMessage()
    message.sender = 'bm@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = bm.user.email()
    message.subject = "(%s) %s" % (app_identity.get_application_id(), bm.title)
    message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, dtf(bm.data), bm.url, bm.comment)
    message.send()


def send_digest(email, html, title):
    message = mail.EmailMessage()
    message.sender = 'bm@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = email
    message.subject = title
    message.html = html
    message.send()


def tag_set(bmq):
    tagset = []
    for bm in bmq:
        for tag in bm.tags:
            if not tag in tagset:
                tagset.append(tag)
    return tagset


def mys_off(user):
    ui = UserInfo.query(UserInfo.user == user).get()
    if ui.mys == True:
        ui.mys = False
        ui.put()
        return 'was_true'


def mys_on(user):
    ui = UserInfo.query(UserInfo.user == user).get()
    if ui.mys == False:
        ui.mys = True
        ui.put()
