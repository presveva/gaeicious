#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import jinja2
from google.appengine.api import urlfetch, files, images
from google.appengine.api import mail, app_identity, search
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from .models import Bookmarks, UserInfo
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser
from libs.feedparser import parse

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
dtf = lambda value: value.strftime('%d/%m/%Y %H:%M')
appid = app_identity.get_application_id()
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates']))
jinja_environment.filters['dtf'] = dtf
config = {}


def pop_feed(feedk, e=0):
    feed = feedk.get()
    parsed = fetch_feed(feed.feed)
    if parsed:
        try:
            entry = parsed['items'][e]
            while feed.last_id != entry.id:
                u = feed.ui
                t = entry['title']
                o = entry['link']
                c = build_comment(entry)
                deferred.defer(submit_bm, feedk, u, t, o, c, _queue='admin')
                e += 1
                entry = parsed['items'][e]
            feed.last_id = parsed['items'][0].id
            feed.put()
        except:
            pass


def submit_bm(feedk, uik, title, url, comment):
    url_fetched = fetch_url(url)
    url_candidate = url_fetched.lstrip().rstrip().split(
        '?utm_source')[0].split('&feature')[0]
    url_parsed = urlparse(url_candidate)

    name = url_parsed.path.split('/')[-1]
    ext = name.split('.')[-1].lower()
    bm_domain = url_parsed.netloc
    bm_title = url_candidate if title == '' or None else title

    if bm_domain == 'www.youtube.com':
        query = parse_qs(url_parsed.query)
        bm_url = 'http://www.youtube.com/watch?v=%s' % query["v"][0]
        bm_comment = """<embed width="640" height="360" src="http://www.youtube.com/v/%s"
        type="application/x-shockwave-flash"> </embed>""" % query["v"][0]

    elif bm_domain == 'vimeo.com':
        bm_url = 'http://vimeo.com/%s' % name
        bm_comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff"
        width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen
        allowFullScreen></iframe>''' % name

    elif bm_domain == 'avaxhome.bz':
        bm_url = url_candidate.replace('.bz/', '.ws/', 1)
        bm_domain = 'avaxhome.ws'
        bm_comment = comment

    elif ext in ['jpg', 'png', 'jpeg', 'gif']:
        bm_url = url_candidate
        blob_key = upload_to_blobstore(url_candidate, ext)
        bm_comment = '<img src="%s" />' % images.get_serving_url(blob_key, size=1600)

    elif ext in ['mp3', 'flac', 'aac', 'ogg']:
        bm_url = url_candidate
        bm_comment = '''<embed type="application/x-shockwave-flash"
        src="http://www.google.com/reader/ui/3523697345-audio-player.swf"
        quality="best" flashvars="audioUrl=%s" width="433" height="27">
        </embed>''' % url_candidate

    else:
        bm_url = url_candidate
        if len(bm_title) > 80 and bm_domain != 'twitter.com':
            bm_comment = '<b>%s</b><br>' % bm_title + comment
        else:
            bm_comment = comment

    copie = Bookmarks.query(Bookmarks.ui == uik,
                            Bookmarks.url == bm_url,
                            Bookmarks.feed == feedk)

    if copie.get() is None:
        bmk = Bookmarks(ui=uik, feed=feedk, url=bm_url, title=bm_title,
                        domain=bm_domain, comment=bm_comment).put()

        if feedk is None and uik.get().mys is True:
            deferred.defer(send_bm, bmk, _queue="admin")
        elif feedk is not None and feedk.get().notify == 'email':
            deferred.defer(send_bm, bmk, _queue="admin")


def build_comment(entry):
    try:
        return entry['content'][0].value
    except KeyError:
        try:
            return entry['description']
        except KeyError:
            return 'no comment'


def fetch_feed(feed_feed):
    try:
        result = urlfetch.fetch(str(feed_feed), deadline=60)
        return parse(result.content)
    except:
        return False


def fetch_url(url):
    try:
        result = urlfetch.fetch(
            url=url, follow_redirects=True, allow_truncated=True, deadline=60)
        if result.status_code == 200 and result.final_url:
            return result.final_url
        else:
            return url
    except:
        return url


def index_bm(key):
    bm = key.get()
    index = search.Index(name=str(bm.ui.id()))
    doc = search.Document(doc_id=str(bm.id), fields=[
                          search.TextField(name='url', value=bm.url),
                          search.TextField(name='title', value=bm.title),
                          search.HtmlField(name='comment', value=bm.comment)
                          ])
    try:
        index.put(doc)
    except search.Error:
        pass


def delete_bms(uik, cursor=None):
    bmq = Bookmarks.query(Bookmarks.ui == uik,
                          Bookmarks.trashed == True)
    bms, cur, more = bmq.fetch_page(10, start_cursor=cursor)
    ndb.delete_multi([bm.key for bm in bms])
    if more:
        deferred.defer(delete_bms, uik, cur)


def login_required(handler_method):
    def check_login(self, *args, **kwargs):
        screen_name = self.request.cookies.get('screen_name')
        if not screen_name:
            self.redirect('/')
        else:
            handler_method(self, *args, **kwargs)
    return check_login


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
        screen_name = self.request.cookies.get('screen_name')
        ui = UserInfo.get_by_id(screen_name)
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        ui.delicious = blob_info.key()
        ui.put()
        deferred.defer(delicious, ui.key, _queue="delicious")
        self.redirect('/')

# Delicious import


def delicious(uik):
    blob_reader = blobstore.BlobReader(
        uik.get().delicious, buffer_size=1048576)
    parser = BookmarkParser()
    parser.feed(blob_reader.read())
    parser.close()

    was = mys_off(uik)
    for bm in parser.bookmarks:
        f = None
        u = uik
        t = bm['title']
        o = bm['url']
        c = bm['comment']
        deferred.defer(
            submit_bm, f, u, t, o, c, _queue="delicious", _countdown=300)
    if was == 'was_true':
        deferred.defer(mys_on, uik, _queue="delicious")


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


def send_bm(bmk):
    bm = bmk.get()
    sender = 'bm@%s.appspotmail.com' % appid
    subject = "[%s] %s" % (appid, bm.title)
    html = """
<html> <table> <tbody>
    <tr> <td><b>%s</b> (%s)</td> </tr>
    <tr> <td>%s</td> </tr>
    <hr>
    <tr> <td>%s</td> </tr>
</tbody> </table> </html>
""" % (bm.title, dtf(bm.data), bm.url, bm.comment)
    mail.send_mail(sender=sender, to=bm.ui.get().email,
                   subject=subject, body=html, html=html)


def mys_off(uik):
    ui = uik.get()
    if ui.mys is True:
        ui.mys = False
        ui.put()
        return 'was_true'


def mys_on(uik):
    ui = uik.get()
    if ui.mys is False:
        ui.mys = True
        ui.put()
