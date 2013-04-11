#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import with_statement
import util
from webapp2 import RequestHandler
from google.appengine.api import users, urlfetch, files, images
from google.appengine.ext import deferred, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from models import Feeds, Bookmarks, UserInfo
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser
from libs.feedparser import parse


class AddFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()
        self.redirect(self.request.referer)

    def post(self):
        user = users.get_current_user()
        feed = self.request.get('url')
        q = Feeds.query(Feeds.user == user, Feeds.feed == feed)
        if user and q.get() is None:
            d = parse(str(feed))
            feed_k = Feeds(feed=feed,
                           title=d['channel']['title'],
                           link=d['channel']['link'],
                           user=user,
                           last_id=d['items'][2].id).put()
            deferred.defer(pop_feed, feed_k, _queue="user")
            self.redirect('/feeds')
        else:
            self.redirect('/')


def pop_feed(feedk):
    feed = feedk.get()
    result = urlfetch.fetch(str(feed.feed), deadline=60)
    d = parse(result.content)
    e = 0
    try:
        entry = d['items'][e]
        while str(feed.last_id) != str(entry.id):
            u = feed.user
            t = entry['title']
            o = entry['link']
            try:
                c = entry['content'][0].value
            except KeyError:
                try:
                    c = entry['description']
                except KeyError:
                    c = 'no comment'
            deferred.defer(submit_bm, feedk, u, t, o, c)
            e += 1
            entry = d['items'][e]
    except IndexError:
        pass
    feed.last_id = str(d.entries[0].id)
    feed.put()


class AddBM(RequestHandler):
    def get(self):
        submit_bm(feed=None,
                  user=users.User("%s" % self.request.get('user')),
                  title=self.request.get('title'),
                  url=self.request.get('url'),
                  comment=self.request.get('comment'))
        self.redirect('/')


class CopyBM(RequestHandler):
    def get(self):
        old = Bookmarks.get_by_id(int(self.request.get('bm')))
        deferred.defer(submit_bm,
                       feed=None,
                       user=users.get_current_user(),
                       title=old.title,
                       url=old.url,
                       comment=old.comment)


def submit_bm(feed, user, title, url, comment):
    bm = Bookmarks()

    result = urlfetch.fetch(url=url, follow_redirects=True, allow_truncated=True, deadline=60)
    if result.status_code == 200 and result.final_url:
        a = result.final_url
    elif result.status_code == 500:
        pass
    else:
        a = url

    url_candidate = a.lstrip().rstrip().split('?utm_source')[0].split('&feature')[0]

    copie = Bookmarks.query(Bookmarks.url == url_candidate,
                            Bookmarks.user == user,
                            Bookmarks.trashed == False)
    if copie.get():
        for cp in copie:
            cp.archived = False
            cp.put()

    url_parsed = urlparse(url_candidate)
    query = parse_qs(url_parsed.query)
    name = url_parsed.path.split('/')[-1]
    ext = name.split('.')[-1].lower()

    bm.title = url_candidate if title == '' or None else title

    if url_parsed.netloc == 'www.youtube.com':
        bm.url = 'http://www.youtube.com/watch?v=%s' % query["v"][0]
        bm.comment = """<embed
        width="640" height="360"
        src="http://www.youtube.com/v/%s"
        type="application/x-shockwave-flash">
        </embed>""" % query["v"][0]

    elif url_parsed.netloc == 'vimeo.com':
        bm.url = 'http://vimeo.com/%s' % name
        bm.comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff"
        width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen
        allowFullScreen></iframe>''' % name

    elif ext in ['jpg', 'png', 'jpeg', 'gif']:
        bm.url = url_candidate
        blob_key = upload_to_blobstore(url_candidate, ext)
        bm.comment = '<img src="%s" />' % images.get_serving_url(blob_key, size=1600)
    else:
        bm.comment = comment
        bm.url = url_candidate

    bm.domain = url_parsed.netloc
    bm.user = user
    bm.feed = feed
    bm.put()
    Bookmarks.index_bm(bm.key)

    ui = UserInfo.get_or_insert(str(user.user_id()), user=user)
    if feed is None and ui.mys is True:
        deferred.defer(util.send_bm, bm.key, _queue="user")
    elif feed is not None and feed.get().notify == 'email':
        deferred.defer(util.send_bm, bm.key)


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
        deferred.defer(delicious, ui.delicious, user, _queue="delicious")

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
