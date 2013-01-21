#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import jinja2
import datetime
import logging
from google.appengine.api import mail, app_identity, search
from google.appengine.ext import deferred, ndb
from models import Bookmarks, UserInfo


def dtf(value, format='%d/%m/%Y - %H:%M UTC'):
    return value.strftime(format)

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates']))
jinja_environment.filters['dtf'] = dtf

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key',
    'backends': {'memcache': 'webapp2_extras.appengine.sessions_memcache.MemcacheSessionFactory'}
}


def index_bms(ui):
    bmq = Bookmarks.query(Bookmarks.user == ui.user)
    for bm in bmq:
        deferred.defer(index_bm, bm.key,
                       _target="worker",
                       _queue='admin')


def index_bm(bmk):
    bm = bmk.get()
    index = search.Index(name=bm.user.user_id())
    doc = search.Document(doc_id=str(bm.id),
                          fields=[
                          search.TextField(name='url', value=bm.url),
                          search.TextField(name='title', value=bm.title),
                          search.HtmlField(name='comment', value=bm.comment)
                          ])
    try:
        index.put(doc)
    except search.Error:
        logging.exception('Add failed')


def remove_bm(bmk):
    bm = bmk.get()
    index = search.Index(name=bm.user.user_id())
    index.remove(str(bm.id))


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
        queue = []
        for bm in bmq:
            bm.trashed = True
            queue.append(bm.key)
        ndb.put_multi(queue)


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
