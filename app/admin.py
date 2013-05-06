#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import util
import datetime
import webapp2
from webapp2_extras import routes
from google.appengine.ext import ndb, deferred
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


app = ndb.toplevel(webapp2.WSGIApplication([
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/cron_trash', cron_trash),
    ])
], debug=util.debug, config=util.config))

if __name__ == "__main__":
    app.run()
