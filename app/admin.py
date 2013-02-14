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


class ReceiveMail(webapp2.RequestHandler):
    def post(self):
        message = mail.InboundEmailMessage(self.request.body)
        texts = message.bodies('text/plain')
        for text in texts:
            txtmsg = ""
            txtmsg = text[1].decode()
        submit_bm(feed=None,
                  user=users.User(utils.parseaddr(message.sender)[1]),
                  url=txtmsg.encode('utf8'),
                  title=self.get_subject(txtmsg.encode('utf8'), message),
                  comment='Sent via email')

    def get_subject(self, o, message):
        from email import header
        try:
            return header.decode_header(message.subject)[0][0]
        except:
            return o


class CheckFeeds(webapp2.RequestHandler):
    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            deferred.defer(submit.pop_feed, feedk)


class SendDigest(webapp2.RequestHandler):
    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            if feed.notify == 'digest':
                deferred.defer(util.feed_digest, feedk)


class SendActivity(webapp2.RequestHandler):
    def get(self):
        for ui in UserInfo.query():
            if ui.daily:
                deferred.defer(util.daily_digest, ui.key)


class cron_trash(webapp2.RequestHandler):
    def get(self):
        delta = datetime.timedelta(days=7)
        now = datetime.datetime.now()
        period = now - delta
        bmq = Bookmarks.query(Bookmarks.trashed == True,
                              Bookmarks.data < period)
        ndb.delete_multi([bm.key for bm in bmq])


app = ndb.toplevel(webapp2.WSGIApplication([
    webapp2.Route('/_ah/mail/post@.*', ReceiveMail),
    routes.RedirectRoute('/admin/', AdminPage, name='Admin', strict_slash=True),
    routes.PathPrefixRoute('/admin', [
        webapp2.Route('/digest', SendDigest),
        webapp2.Route('/activity', SendActivity),
        webapp2.Route('/check', CheckFeeds),
        webapp2.Route('/cron_trash', cron_trash),
        ])
    ], debug=util.debug, config=util.config))

if __name__ == "__main__":
    app.run()
