#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import webapp2
import util
import submit
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


class indicizza(webapp2.RequestHandler):
    def get(self):
        for ui in UserInfo.query():
            deferred.defer(util.index_bms,
                           ui,
                           _target='worker',
                           _queue='admin')
            self.redirect('/')


class ReceiveMail(webapp2.RequestHandler):
    def post(self):
        message = mail.InboundEmailMessage(self.request.body)
        texts = message.bodies('text/plain')
        for text in texts:
            txtmsg = ""
            txtmsg = text[1].decode()
        f = None
        u = users.User(utils.parseaddr(message.sender)[1])
        o = txtmsg.encode('utf8')
        t = self.get_subject(o, message)
        c = 'Sent via email'
        submit_bm(f, u, t, o, c)


class CheckFeeds(webapp2.RequestHandler):
    def get(self):
        for feed in Feeds.query():
            deferred.defer(submit.pop_feed, feed.key, _target="worker", _queue="admin")


class SendDigest(webapp2.RequestHandler):
    def get(self):
        for feed in Feeds.query():
            if feed.notify == 'digest':
                deferred.defer(feed_digest, feed.key, _target="worker", _queue="emails")


class SendActivity(webapp2.RequestHandler):
    def get(self):
        for ui in UserInfo.query():
            if ui.daily:
                deferred.defer(daily_digest, ui.user, _target="worker", _queue="emails")


class cron_trash(webapp2.RequestHandler):
    def get(self):
        delta = datetime.timedelta(days=30)
        now = datetime.datetime.now()
        period = now - delta
        bmq = Bookmarks.query(Bookmarks.trashed == True)
        bmq = bmq.filter(Bookmarks.data < period)
        ndb.delete_multi([bm.key for bm in bmq])


app = ndb.toplevel(webapp2.WSGIApplication([
    webapp2.Route('/_ah/mail/post@.*', ReceiveMail),
    routes.RedirectRoute('/admin/', AdminPage, name='Admin', strict_slash=True),
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/indicizza', indicizza),
        webapp2.Route('/cron_trash', cron_trash),
        ])
    ], debug=util.debug, config=util.config))


def admin():
    app.run()

if __name__ == "__main__":
    admin()
