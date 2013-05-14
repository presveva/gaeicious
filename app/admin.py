#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import util
import datetime
import webapp2
from webapp2_extras import routes
from google.appengine.ext import ndb, deferred
from google.appengine.api import search
from models import Feeds, Bookmarks, UserInfo


class CheckFeeds(webapp2.RequestHandler):

    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            deferred.defer(util.pop_feed, feedk, _queue='feed')


class SendDigest(webapp2.RequestHandler):

    def get(self):
        for feed in Feeds.query():
            if feed.notify == 'digest':
                deferred.defer(util.feed_digest, feed.key, _queue='email')


class SendActivity(webapp2.RequestHandler):

    def get(self):
        for ui in UserInfo.query():
            if ui.daily:
                deferred.defer(util.daily_digest, ui.key, _queue='email')


class cron_trash(webapp2.RequestHandler):

    def get(self):
        delta = datetime.timedelta(days=7)
        now = datetime.datetime.now()
        period = now - delta
        bmq = Bookmarks.query(Bookmarks.trashed == True,
                              Bookmarks.data < period)
        ndb.delete_multi([bm.key for bm in bmq])


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
        deferred.defer(reindex, _queue='admin')
        self.redirect('/admin')


def reindex(cursor=None):
    bmq = Bookmarks.query()
    bms, cur, more = bmq.fetch_page(10, start_cursor=cursor)
    for bm in bms:
        deferred.defer(util.index_bm, bm.key, _queue='admin')
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
        deferred.defer(delatt, ent, prop, _queue='admin')
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
        deferred.defer(itera, model, prop, _queue='admin')
        self.redirect('/admin')


def itera(model, prop=None, cursor=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        deferred.defer(make_some, ent, prop, _queue='admin')
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
    ])
], debug=util.debug, config=util.config))

if __name__ == "__main__":
    app.run()
