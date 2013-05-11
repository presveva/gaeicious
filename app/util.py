#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import jinja2
import datetime
from google.appengine.api import urlfetch, files, images, mail, app_identity
from google.appengine.ext import deferred, blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
from models import Bookmarks, UserInfo
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser
from libs.feedparser import parse

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
dtf = lambda value: value.strftime('%d/%m/%Y %H:%M')
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates']))
jinja_environment.filters['dtf'] = dtf
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key'}


def submit_bm(feedk, uik, title, url, comment):
    bm = Bookmarks()

    result = urlfetch.fetch(
        url=url, follow_redirects=True, allow_truncated=True, deadline=60)
    if result.status_code == 200 and result.final_url:
        a = result.final_url
    elif result.status_code == 500:
        pass
    else:
        a = url

    url_candidate = a.lstrip().rstrip().split(
        '?utm_source')[0].split('&feature')[0]

    url_parsed = urlparse(url_candidate)
    query = parse_qs(url_parsed.query)
    name = url_parsed.path.split('/')[-1]
    ext = name.split('.')[-1].lower()

    bm.title = url_candidate if title == '' or None else title
    bm.domain = url_parsed.netloc
    bm.ui = uik
    bm.feed = feedk

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
        bm.comment = '<img src="%s" />' % images.get_serving_url(
            blob_key, size=1600)
    else:
        bm.comment = bm.title if comment == '' or None else comment
        bm.url = url_candidate

    copie = Bookmarks.query(Bookmarks.url == bm.url,
                            Bookmarks.ui == uik,
                            Bookmarks.feed == feedk)
    if copie.get() is None:
        bm.put()
        Bookmarks.index_bm(bm.key)

        if feedk is None and uik.get().mys is True:
            deferred.defer(send_bm, bm.key, _queue="email")
        elif feedk is not None and feedk.get().notify == 'email':
            deferred.defer(send_bm, bm.key, _queue="email")


def login_required(handler_method):
    def check_login(self, *args, **kwargs):
        screen_name = self.request.cookies.get('screen_name')
        if not screen_name:
            self.redirect('/')
        else:
            handler_method(self, *args, **kwargs)
    return check_login


def pop_feed(feedk):
    feed = feedk.get()
    result = urlfetch.fetch(str(feed.feed), deadline=60)
    d = parse(result.content)
    e = 0
    try:
        entry = d['items'][e]
        while feed.last_id != entry.id:
            u = feed.ui
            t = entry['title']
            o = entry['link']
            try:
                c = entry['content'][0].value
            except KeyError:
                try:
                    c = entry['description']
                except KeyError:
                    c = 'no comment'
            deferred.defer(submit_bm, feedk, u, t, o, c, _queue='bookmark')
            e += 1
            entry = d['items'][e]
        feed.last_id = d['items'][0].id
        feed.put()
    except IndexError:
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
        deferred.defer(submit_bm, f, u, t, o, c, _queue="delicious")
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


def daily_digest(uik):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    bmq = Bookmarks.query(Bookmarks.ui == uik,
                          Bookmarks.trashed == False,
                          Bookmarks.data > period).order(-Bookmarks.data)
    title = '[%s] Daily digest for your activity: %s' % (
        app_identity.get_application_id(), dtf(now))
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get() is not None:
        deferred.defer(
            send_digest, uik.get().email, html, title, _queue='email')


def feed_digest(feedk):
    delta = datetime.timedelta(days=1)
    now = datetime.datetime.now()
    period = now - delta
    feed = feedk.get()
    bmq = Bookmarks.query(Bookmarks.ui == feed.ui,
                          Bookmarks.feed == feed.key,
                          Bookmarks.trashed == False,
                          Bookmarks.data > period).order(-Bookmarks.data)
    title = '[%s] Daily digest for %s' % (
        app_identity.get_application_id(), feed.title)
    template = jinja_environment.get_template('digest.html')
    values = {'bmq': bmq, 'title': title}
    html = template.render(values)
    if bmq.get() is not None:
        deferred.defer(
            send_digest, feed.ui.get().email, html, title, _queue='email')
        queue = []
        for bm in bmq:
            bm.archived = True
            queue.append(bm)
        ndb.put_multi(queue)


def send_bm(bmk):
    bm = bmk.get()
    sender = 'bm@%s.appspotmail.com' % app_identity.get_application_id()
    subject = "[%s] %s" % (app_identity.get_application_id(), bm.title)
    html = """
<html> <table> <tbody>
    <tr> <td><b>%s</b> (%s)</td> </tr>
    <tr> <td>%s</td> </tr>
    <hr>
    <tr> <td>%s</td> </tr>
</tbody> </table> </html>
""" % (bm.title, dtf(bm.data), bm.url, bm.comment)
    mail.send_mail(sender=sender,
                   to=bm.ui.get().email,
                   subject=subject,
                   body=html,
                   html=html)


def send_digest(email, html, title):
    message = mail.EmailMessage()
    message.sender = 'bm@%s.appspotmail.com' % app_identity.get_application_id()
    message.to = email
    message.subject = title
    message.html = html
    message.send()


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
