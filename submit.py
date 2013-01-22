#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import with_statement
import util
from webapp2 import RequestHandler
from google.appengine.api import users, urlfetch, files, images
from google.appengine.ext import ndb, deferred, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from models import Feeds, Bookmarks, UserInfo
from email import header
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser


class AddFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()
        self.redirect(self.request.referer)

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
                feed = Feeds(blog=p.feed.title,
                             root=p.feed.link,
                             user=user,
                             feed=url,
                             url=d.link)
                feed.put()
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

    def get_subject(self, o, message):
        try:
            t = header.decode_header(message.subject)[0][0]
            return t
        except:
            return o


class CopyBM(RequestHandler):
    def get(self):
        old = Bookmarks.get_by_id(int(self.request.get('bm')))
        f = None
        u = users.get_current_user()
        t = old.title
        o = old.url
        c = old.comment
        deferred.defer(submit_bm, f, u, t, o, c, _queue="admin")


def submit_bm(feed, user, title, url, comment):
    try:
        bm = Bookmarks()

        result = urlfetch.fetch(url=url, follow_redirects=True, allow_truncated=True, deadline=60)
        ui_f = UserInfo.query(UserInfo.user == user).get()
        if result.status_code == 200 and result.final_url:
            a = result.final_url
        elif result.status_code == 500:
            pass
        else:
            a = url
        b = a.lstrip().rstrip()
        c = b.split('?utm_source')[0]
        url_candidate = c.split('&feature')[0]

        url_parsed = urlparse(url_candidate)
        query = parse_qs(url_parsed.query)
        name = url_parsed.path.split('/')[-1]
        ext = name.split('.')[-1].lower()

        if title == '' or title == None:
            bm.title = url_candidate
        else:
            bm.title = title

        if url_parsed.netloc == 'www.youtube.com':
            video = query["v"][0]
            bm.url = 'http://www.youtube.com/watch?v=%s' % video
            bm.comment = """<embed
            width="640" height="360"
            src="http://www.youtube.com/v/%s"
            type="application/x-shockwave-flash">
            </embed>""" % video

        elif url_parsed.netloc == 'vimeo.com':
            video = name
            bm.url = 'http://vimeo.com/%s' % video
            bm.comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff"
            width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen
            allowFullScreen></iframe>''' % video

        elif ext in ['jpg', 'png', 'jpeg', 'gif']:
            bm.url = url_candidate
            blob_key = upload_to_blobstore(url_candidate, ext)
            bm.blob_key = blob_key
            bm.comment = '<img src="%s" />' % images.get_serving_url(blob_key, size=1600)
        else:
            bm.comment = comment
            bm.url = url_candidate

        bm.domain = url_parsed.netloc
        bm.user = user
        bm.feed = feed
        bm.put()
        util.index_bm(bm.key)
        try:
            if bm.feed.get().notify == 'email':
                deferred.defer(util.send_bm, bm.key, _queue="emails")
        except:
            if ui_f.mys:
                deferred.defer(util.send_bm, bm.key, _queue="emails")
    except:
        pass


def upload_to_blobstore(url_candidate, ext):
    result = urlfetch.fetch(url=url_candidate)
    if result.status_code == 200:
        data = result.content
        mime_type = "img/%s" % ext
        file_name = files.blobstore.create(mime_type=mime_type)
        with files.open(file_name, 'a') as f:
            f.write(data)
        files.finalize(file_name)
        blob_key = files.blobstore.get_blob_key(file_name)
        return blob_key


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


def pop_feed(feedk):
    from libs.feedparser import parse
    feed = feedk.get()
    result = urlfetch.fetch(url="%s" % feed.feed, deadline=60)
    p = parse(result.content)
    e = 0
    try:
        entry = p['items'][e]
        while feed.url != entry['link']:
            f = feedk
            u = feed.user
            t = entry['title']
            o = entry['link']
            try:
                c = entry['description']
            except KeyError:
                c = 'no comment'
            deferred.defer(submit_bm, f, u, t, o, c, _queue="importer")
            e += 1
            entry = p['items'][e]
    except IndexError:
        pass
    s = p['items'][0]
    feed.url = s['link']
    feed.put()

# Delicious import


def delicious(blob_key, user):
    blob_reader = blobstore.BlobReader(blob_key, buffer_size=1048576)
    parser = BookmarkParser()
    parser.feed(blob_reader.read())
    parser.close()

    was = util.mys_off(user)
    for bm in parser.bookmarks:
        f = None
        u = user
        t = bm['title']
        o = bm['url']
        c = bm['comment']
        deferred.defer(submit_bm, f, u, t, o, c, _queue="delicious")
    if was == 'was_true':
        deferred.defer(util.mys_on, user, _queue="delicious")


class BookmarkParser(HTMLParser):
    def reset(self):
        HTMLParser.reset(self)
        self.bookmarks = []
        self.last_bookmark = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            bookmark = {}
            bookmark['title'] = u''
            bookmark['comment'] = u''

            for k, v in attrs:
                if k == 'href':
                    bookmark['url'] = v

            self.bookmarks.append(bookmark)
            self.last_bookmark = bookmark

    def handle_data(self, data):
        if self.lasttag == 'a' and self.last_bookmark['title'] == '':
            self.last_bookmark['title'] = str(data)

        if self.lasttag == 'dd' and self.last_bookmark['comment'] == '':
            self.last_bookmark['comment'] = str(data)
