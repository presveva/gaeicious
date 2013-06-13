#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import datetime
import webapp2
from webapp2_extras import routes
from google.appengine.ext import ndb, deferred
from google.appengine.api import search, mail
from . import util
from .models import Feeds, Bookmarks, UserInfo


class CheckFeeds(webapp2.RequestHandler):

    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            # util.check_feed(feedk)
            deferred.defer(util.check_feed, feedk, _queue='check')


class SendDigest(webapp2.RequestHandler):

    def get(self):
        for feedk in Feeds.query(Feeds.notify == 'digest').fetch(keys_only=True):
            deferred.defer(feed_digest, feedk, _queue='email')


def feed_digest(feedk):
    bmq = Bookmarks.query(Bookmarks.feed == feedk,
                          Bookmarks.archived == False,
                          Bookmarks.trashed == False)
    feed = feedk.get()
    email = feed.ui.get().email
    if bmq.count() > 4 and email is not None:
        # title = 'bla'
        title = '[%s] Digest for %s' % (util.appid, feed.title)
        template = util.jinja_environment.get_template('digest.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.appid
        mail.send_mail(
            sender=sender, to=email, subject=title, body=html, html=html)
        queue = []
        for bm in bmq:
            bm.trashed = True
            queue.append(bm)
        ndb.put_multi(queue)


class SendActivity(webapp2.RequestHandler):

    def get(self):
        for uik in UserInfo.query(UserInfo.daily == True).fetch(keys_only=True):
            deferred.defer(activity_digest, uik, _queue='email')


def activity_digest(uik):
    delta = datetime.timedelta(hours=12)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.ui == uik, Bookmarks.trashed == False,
                          Bookmarks.data > period).order(-Bookmarks.data)
    email = uik.get().email
    if bmq.get() is not None and email is not None:
        title = '[%s] Daily digest for your activity: %s' % (
            util.appid, util.dtf(now))
        template = util.jinja_environment.get_template('activity.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.appid
        mail.send_mail(
            sender=sender, to=email, subject=title, body=html, html=html)


class cron_trash(webapp2.RequestHandler):

    def get(self):
        delta = datetime.timedelta(days=7)
        now = datetime.datetime.now()
        period = now - delta
        bmq = Bookmarks.query(Bookmarks.trashed == True,
                              Bookmarks.data < period).fetch(keys_only=True)
        ndb.delete_multi(bmq)


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


class reindex_all(webapp2.RequestHandler):

    def get(self):
        deferred.defer(reindex)
        self.redirect('/admin')


def reindex(cursor=None):
    bmq = Bookmarks.query()
    bms, cur, more = bmq.fetch_page(10, start_cursor=cursor)
    for bm in bms:
        deferred.defer(util.index_bm, bm.key)
    if more:
        deferred.defer(reindex, cur)


class del_attr(webapp2.RequestHandler):

    """Delete property unused after a schema update"""
    def post(self):
        model = str(self.request.get('model'))
        prop = str(self.request.get('prop'))
        deferred.defer(iter_entity, model, prop)
        self.redirect('/admin')


def iter_entity(model, prop, cursor=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        deferred.defer(delatt, ent, prop)
    if more:
        deferred.defer(iter_entity, model, prop, cur)


def delatt(ent, prop):
    if hasattr(ent, prop):
        delattr(ent, prop)
        ent.put()


class Iterator(webapp2.RequestHandler):

    def post(self):
        model = str(self.request.get('model'))
        prop = UserInfo.get_by_id('presveva').key
        deferred.defer(itera, model, prop)
        self.redirect('/admin')


def itera(model, prop=None, cursor=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        deferred.defer(make_some, ent, prop)
    if more:
        deferred.defer(itera, model, prop, cur)


def make_some(ent, prop):
    if ent.ui != prop:
        ent.ui = prop
        ent.put()


app = ndb.toplevel(webapp2.WSGIApplication([
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/cron_trash', cron_trash),
        webapp2.Route('/delete_index', DeleteIndex),
        webapp2.Route('/del_attr', del_attr),
        webapp2.Route('/reindex_all', reindex_all),
        webapp2.Route('/iterator', Iterator),
    ])], debug=util.debug, config=util.config))
