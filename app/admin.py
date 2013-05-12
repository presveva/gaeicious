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


class delete_index(webapp2.RequestHandler):

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
        for bmk in Bookmarks.query().fetch(keys_only=True):
            Bookmarks.index_bm(bmk)


class del_attr(webapp2.RequestHandler):

    def post(self):
        model = str(self.request.get('model'))
        prop = str(self.request.get('prop'))
        deferred.defer(update_schema, model, prop)
        self.redirect('/admin')
        # for ent in qry:
        #     deferred.defer(delatt_ent, ent, prop, _queue='admin')
        # self.redirect('/admin')


def update_schema(model, prop, cursor=None):
    qry = ndb.gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        deferred.defer(delatt, ent, prop, _queue='admin')
    if more:
        deferred.defer(update_schema, model, prop, cur)


def delatt(ent, prop):
    if hasattr(ent, prop):
        delattr(ent, prop)
        ent.put()

app = ndb.toplevel(webapp2.WSGIApplication([
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/cron_trash', cron_trash),
        webapp2.Route('/delete_index', delete_index),
        webapp2.Route('/del_attr', del_attr),
        webapp2.Route('/reindex_all', reindex_all),
    ])
], debug=util.debug, config=util.config))

if __name__ == "__main__":
    app.run()
