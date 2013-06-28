#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import jinja2
from google.appengine.api import urlfetch, mail, app_identity
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from .models import Bookmarks, UserInfo
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser
from libs.feedparser import parse

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
dtf = lambda value: value.strftime('%d/%m/%Y %H:%M')
brand = app_identity.get_application_id()
upload_url = blobstore.create_upload_url('/upload')
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates']))
jinja_environment.filters['dtf'] = dtf
config = {}


def submit_bm(feedk, uik, title, url, comment):
    url_fetched = fetch_url(url)
    url_candidate = url_fetched.lstrip().rstrip().split(
        '?utm_source')[0].split('&feature')[0]
    url_parsed = urlparse(url_candidate)

    name = url_parsed.path.split('/')[-1]
    ext = name.split('.')[-1].lower()
    bm_domain = url_parsed.netloc
    bm_title = url_candidate if title == '' or None else title
    avax = ['avaxho.me', 'avaxhome.bz', 'avaxhome.ws']

    if bm_domain == 'www.youtube.com':
        query = parse_qs(url_parsed.query)
        bm_url = 'http://www.youtube.com/watch?v=%s' % query["v"][0]
        bm_comment = """<embed width="757" height="430" src="http://www.youtube.com/v/%s"
        type="application/x-shockwave-flash"> </embed>""" % query["v"][0]

    elif bm_domain == 'vimeo.com':
        bm_url = 'http://vimeo.com/%s' % name
        bm_comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff"
        width="757" height="430" frameborder="0" webkitAllowFullScreen mozallowfullscreen
        allowFullScreen></iframe>''' % name

    elif bm_domain in avax:
        bm_url = url_candidate.replace(avax[1], avax[0]).replace(avax[2], avax[0])
        bm_domain = avax[0]
        bm_comment = comment

    elif ext in ['jpg', 'png', 'jpeg', 'gif']:
        bm_url = url_candidate
        bm_comment = '<img src="%s" width="757"/>' % url_candidate

    elif ext in ['mp3', 'flac', 'aac', 'ogg']:
        bm_url = url_candidate
        bm_comment = '''<embed type="application/x-shockwave-flash"
        src="http://www.google.com/reader/ui/3523697345-audio-player.swf"
        quality="best" flashvars="audioUrl=%s" width="433" height="27">
        </embed>''' % url_candidate

    else:
        bm_url = url_candidate
        bm_comment = comment

    bm = Bookmarks.get_or_insert(bm_url, parent=uik, feed=feedk,
                                 title=bm_title, domain=bm_domain,
                                 comment=bm_comment)

    if feedk is None and uik.get().mys is True:
        deferred.defer(send_bm, bm.key, _queue='email')
    elif feedk is not None and feedk.get().notify == 'email':
        deferred.defer(send_bm, bm.key, _queue='email')


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
    except urlfetch.Error:
        return False


def fetch_url(url):
    try:
        result = urlfetch.fetch(
            url=url, follow_redirects=True, allow_truncated=True, deadline=60)
        return result.final_url if result.final_url else url
    except urlfetch.Error:
        return url


def delete_bms(uik, cursor=None):
    bmq = Bookmarks.query(Bookmarks.stato == 'trash', ancestor=uik)
    bms, cur, more = bmq.fetch_page(50, start_cursor=cursor, keys_only=True)
    ndb.delete_multi(bms)
    if more:
        deferred.defer(delete_bms, uik, cur, _countdown=600)


def login_required(handler_method):
    def check_login(self, *args, **kwargs):
        screen_name = self.request.cookies.get('screen_name')
        if not screen_name:
            self.redirect('/')
        else:
            handler_method(self, *args, **kwargs)
    return check_login


def send_bm(bmk):
    bm = bmk.get()
    sender = 'bm@%s.appspotmail.com' % brand
    subject = "[%s] %s" % (brand, bm.title)
    html = """
<html> <table> <tbody>
    <tr> <td><b>%s</b> (%s)</td> </tr>
    <tr> <td>%s</td> </tr>
    <hr>
    <tr> <td>%s</td> </tr>
</tbody> </table> </html>
""" % (bm.title, dtf(bm.data), bm.key.id(), bm.comment)
    mail.send_mail(sender=sender, to=bm.key.parent().get().email,
                   subject=subject, body=html, html=html)


# Delicious import
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
