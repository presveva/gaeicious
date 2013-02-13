#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import jinja2
import datetime
from google.appengine.api import mail, app_identity
from google.appengine.ext import deferred, ndb
from models import Bookmarks, UserInfo

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

dtf = lambda value: value.strftime('%d/%m/%Y - %H:%M UTC')

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates']))
jinja_environment.filters['dtf'] = dtf

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key'}


def daily_digest(user):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.user == user,
                          Bookmarks.trashed == False,
                          Bookmarks.data > period).order(-Bookmarks.data)
    title = '[%s] Daily digest for your activity: %s' % (app_identity.get_application_id(), dtf(now))
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get() != None:
        deferred.defer(send_digest, user.email(), html, title)


def feed_digest(feedk):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    feed = feedk.get()
    bmq = Bookmarks.query(Bookmarks.user == feed.user,
                          Bookmarks.feed == feed.key,
                          Bookmarks.trashed == False,
                          Bookmarks.data > period).order(-Bookmarks.data)
    title = '[%s] Daily digest for %s' % (app_identity.get_application_id(), feed.link)
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get() != None:
        deferred.defer(send_digest, feed.user.email(), html, title)
        queue = []
        for bm in bmq:
            bm.trashed = True
            queue.append(bm.key)
        ndb.put_multi(queue)


def send_bm(bmk):
    bm = bmk.get()
    sender = 'bm@%s.appspotmail.com' % app_identity.get_application_id()
    subject = "[%s] %s" % (app_identity.get_application_id(), bm.title)
    html = """%s (%s)<br>%s<br><br>%s """ % (bm.title, dtf(bm.data), bm.url, bm.comment)
    mail.send_mail(sender=sender,
              to=bm.user.email(),
              subject=subject,
              body=html,
              html=html)


def send_digest(email, html, title):
    message = mail.EmailMessage()
    message.sender = 'bm@%s.appspotmail.com' % app_identity.get_application_id()
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
