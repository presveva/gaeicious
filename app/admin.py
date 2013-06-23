#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import logging
import datetime
import webapp2
from webapp2_extras import routes
from google.appengine.ext import ndb, deferred
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import search, mail, users
from . import util
from .models import *

is_admin = users.is_current_user_admin()


class AdminPage(webapp2.RequestHandler):

    def get(self):
        continue_url = self.request.get('continue')

        if users.get_current_user():
            url = users.create_logout_url(continue_url)
            text = 'Admin logout'
        else:
            url = users.create_login_url(continue_url)
            text = 'Admin login'
        template = util.jinja_environment.get_template('admin.html')
        self.response.write(template.render({
                            'brand': util.brand, 'text': text,
                            'url': url, 'admin': is_admin}))


# CHECK FEEDS
class CheckFeeds(webapp2.RequestHandler):

    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            deferred.defer(check_feed, feedk, _queue='check')


def check_feed(feedk, e=0):
    feed = feedk.get()
    parsed = util.fetch_feed(feed.feed)
    n = len(parsed['items']) if parsed is not False else 0
    if n > 0 and feed.last_id != parsed['items'][0]['link']:
        entry = parsed['items'][e]
        while feed.last_id != entry['link'] and e < (n - 1):
            deferred.defer(util.submit_bm, feedk=feedk, uik=feed.ui,
                           title=entry['title'], url=entry['link'],
                           comment=util.build_comment(entry),
                           _queue='submit')
            e += 1
            entry = parsed['items'][e]
        feed.last_id = parsed['items'][0]['link']
        feed.put()
        deferred.defer(feed_digest, feedk, _queue='email', _countdown=300)


def feed_digest(feedk):

    bmq = Bookmarks.query(Bookmarks.feed == feedk, Bookmarks.stato == 'inbox')
    feed = feedk.get()
    email = feed.ui.get().email
    if feed.notify == 'digest' and email is not None and bmq.count() > 4:
        title = '[%s] Digest for %s' % (util.brand, feed.title)
        template = util.jinja_environment.get_template('digest.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.brand
        mail.send_mail(sender=sender, subject=title,
                       to=email, body=html, html=html)
        queue = []
        for bm in bmq:
            bm.stato = 'trash'
            queue.append(bm)
        ndb.put_multi(queue)


# 6 HOURS DIGEST
class Activity(webapp2.RequestHandler):

    def get(self):
        for ui in UserInfo.query():
            deferred.defer(cron_trash, ui.key, _queue='worker')
            if ui.daily is True:
                deferred.defer(activity_digest, ui.key, _queue='worker')


def activity_digest(uik):
    delta = datetime.timedelta(hours=6)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.stato == 'inbox',
                          Bookmarks.data > period,
                          ancestor=uik)
    email = uik.get().email
    if bmq.get() is not None and email is not None:
        title = '[%s] Last 6 hours inbox: %s' % (util.brand, util.dtf(now))
        template = util.jinja_environment.get_template('activity.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.brand
        mail.send_mail(sender=sender, subject=title,
                       to=email, body=html, html=html)


def cron_trash(uik):
    delta = datetime.timedelta(days=3)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.data < period,
                          Bookmarks.stato == 'trash',
                          ancestor=uik).fetch(50, keys_only=True)
    ndb.delete_multi(bmq)


# ITERATOR
class Iterator(webapp2.RequestHandler):

    def post(self):
        model = str(self.request.get('model'))
        itera(model)
        self.redirect('/admin')


def itera(model, cursor=None, arg=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(40, start_cursor=cursor)
    count = 0
    dadel = []
    for ent in res:
        if ent.trashed is True:
            dadel.append(ent.key)
            count += 1
        elif ent.key.string_id() is None:
            deferred.defer(make_some, ent, _queue='upgrade')
            count += 1
    ndb.delete_multi(dadel)
    if more and count < 20:
        deferred.defer(itera, model, cur, _queue='upgrade')
    elif more:
        deferred.defer(itera, model, cur, _queue='upgrade', _countdown=1800)


def make_some(ent, arg=None):
    stato = 'archive' if ent.archived else 'inbox'
    Bookmarks.get_or_insert(ent.url, parent=ent.ui, feed=ent.feed,
                            title=ent.title, comment=ent.comment,
                            domain=ent.domain, stato=stato)
    ent.key.delete()


# DELETE SEARCH INDEX
class DeleteIndex(webapp2.RequestHandler):

    def post(self):
        index_name = self.request.get('index_name')
        self.reset_index(index_name)
        self.redirect(self.request.referer)

    def reset_index(self, index_name):
        """Delete all the docs in the given index."""
        doc_index = search.Index(name=index_name)

        while True:
            document_ids = [document.doc_id
                            for document in doc_index.get_range(ids_only=True)]
            if not document_ids:
                break
            doc_index.delete(document_ids)
        doc_index.delete_schema()


# REINDEX ALL BMS
class reindex_all(webapp2.RequestHandler):

    def get(self):
        deferred.defer(reindex)
        self.redirect('/admin')


def reindex(cursor=None):
    bmq = Bookmarks.query().fetch(keys_only=True)
    bms, cur, more = bmq.fetch_page(100, start_cursor=cursor)
    for bmk in bms:
        deferred.defer(index_bm, bmk, _queue='upgrade')
    if more:
        deferred.defer(reindex, cur, _queue='upgrade', _countdown=3600)


def index_bm(key):
    bm = key.get()
    index = search.Index(name=key.parent().string_id())
    doc = search.Document(doc_id=key.urlsafe(), fields=[
        search.TextField(name='url', value=key.string_id()),
        search.TextField(name='title', value=bm.title),
        search.HtmlField(name='comment', value=bm.comment)])
    try:
        index.put(doc)
    except search.Error:
        pass


# DELATTR
class del_attr(webapp2.RequestHandler):

    """Delete property unused after a schema update"""
    def post(self):
        model = str(self.request.get('model'))
        prop = str(self.request.get('prop'))
        iter_entity(model, prop)
        self.redirect('/admin')


def iter_entity(model, prop, cursor=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        deferred.defer(delatt, ent, prop, _queue='upgrade')
    if more:
        deferred.defer(iter_entity, model, prop, cur,
                       _queue='upgrade', _countdown=3600)


def delatt(ent, prop):
    if hasattr(ent, prop):
        delattr(ent, prop)
        ent.put()


class PostViaEmail(InboundMailHandler):

    def receive(self, message):
        email = message.sender.split('<')[1].split('>')[0]
        url = message.bodies('text/plain').next()[1].decode().strip()
        ui = UserInfo.query(UserInfo.email == email).get()
        deferred.defer(util.submit_bm, feedk=None, uik=ui.key,
                       title=message.subject, comment='Sent via email',
                       url=url, _queue='submit')


class BounceHandler(webapp2.RequestHandler):

    def post(self):
        bounce = BounceNotification(self.request.POST)
        logging.error('Bounce original: %s' + str(bounce.original))
        logging.error('Bounce notification: %s' + str(bounce.notification))

app = webapp2.WSGIApplication([
    routes.RedirectRoute('/admin/', AdminPage, name='Admin', strict_slash=True),
    webapp2.Route('/_ah/mail/post@.*', PostViaEmail),
    webapp2.Route('/_ah/bounce', BounceHandler),
    webapp2.Route('/_ah/login_required', AdminPage),
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/activity', Activity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/del_attr', del_attr),
        webapp2.Route('/delete_index', DeleteIndex),
        webapp2.Route('/reindex_all', reindex_all),
        webapp2.Route('/iterator', Iterator),
    ])
], debug=util.debug, config=util.config)
