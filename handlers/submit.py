#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from webapp2 import RequestHandler
from google.appengine.api import users, mail
from google.appengine.ext import ndb, deferred
from google.appengine.ext.webapp import blobstore_handlers
from models import Feeds, Bookmarks, UserInfo
from email import header, utils
from parser import submit_bm, delicious, pop_feed


class AddFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()

    def post(self):
        from libs.feedparser import parse
        user = users.get_current_user()
        url = self.request.get('url')
        p = parse(str(url))
        try:
            d = p['items'][0]
        except IndexError:
            pass
        if user:
            q = Feeds.query(Feeds.user == user, Feeds.url == url)
            if q.get() is None:
                feed = Feeds()

                def txn():
                    feed.blog = p.feed.title
                    feed.root = p.feed.link
                    feed.user = user
                    feed.feed = url
                    feed.url = d.link
                    feed.put()
                ndb.transaction(txn)
                deferred.defer(pop_feed, feed.key, _target="worker", _queue="admin")
            self.redirect(self.request.referer)
        else:
            self.redirect('/')


class AddBM(RequestHandler):
    def get(self):
        f = None
        u = users.User(str(self.request.get('user')))
        t = self.request.get('title')  # .encode('utf8')
        o = self.request.get('url')  # .encode('utf8')
        c = self.request.get('comment')  # .encode('utf8')
        submit_bm(f, u, t, o, c)
        self.redirect('/')


class ReceiveMail(RequestHandler):
    def post(self):
        message = mail.InboundEmailMessage(self.request.body)
        texts = message.bodies('text/plain')
        for text in texts:
            txtmsg = ""
            txtmsg = text[1].decode()
        f = None
        u = users.User(utils.parseaddr(message.sender)[1])
        t = header.decode_header(message.subject)[0][0]
        o = txtmsg.encode('utf8')
        c = 'Sent via email'
        deferred.defer(submit_bm, f, u, t, o, c, _queue="admin")


class CopyBM(RequestHandler):
    def get(self):
        old = Bookmarks.get_by_id(int(self.request.get('bm')))
        f = None
        u = users.get_current_user()
        t = old.title
        o = old.url
        c = old.comment
        deferred.defer(submit_bm, f, u, t, o, c, _queue="admin")


class UploadDelicious(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        user = users.get_current_user()
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        ui = UserInfo.query(UserInfo.user == user).get()
        ui.delicious = blob_info.key()
        ui.put()
        self.redirect('/')
        deferred.defer(delicious, ui.delicious, user, _target="worker", _queue="admin")
