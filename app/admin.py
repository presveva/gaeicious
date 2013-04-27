#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import webapp2
import util
import submit
import datetime
from google.appengine.api import users
from google.appengine.ext import ndb, deferred
from models import *
from main import BaseHandler
from webapp2_extras import routes


class AdminPage(BaseHandler):
    def get(self):
        if users.is_current_user_admin():
            self.response.set_cookie('active-tab', 'admin')
            self.generate('admin.html')
        else:
            self.redirect('/')


class CheckFeeds(webapp2.RequestHandler):
    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            deferred.defer(submit.pop_feed, feedk, _queue='feed')


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


class script(webapp2.RequestHandler):
    def get(self):
        """Delete all the docs in the given index."""
        doc_index = search.Index(name='None')
        while True:
            document_ids = [document.doc_id
                            for document in doc_index.get_range(ids_only=True)]
            if not document_ids:
                break
            doc_index.delete(document_ids)
        # doc_index.deleteSchema()


class cron_trash(webapp2.RequestHandler):
    def get(self):
        delta = datetime.timedelta(days=7)
        now = datetime.datetime.now()
        period = now - delta
        bmq = Bookmarks.query(Bookmarks.trashed == True,
                              Bookmarks.data < period)
        ndb.delete_multi([bm.key for bm in bmq])


app = ndb.toplevel(webapp2.WSGIApplication([
    routes.RedirectRoute('/admin/', AdminPage, name='Admin', strict_slash=True),
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/cron_trash', cron_trash),
        webapp2.Route('/script', script),
    ])
], debug=util.debug, config=util.config))

if __name__ == "__main__":
    app.run()
