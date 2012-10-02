from __future__ import with_statement
from google.appengine.ext import ndb, deferred, blobstore
from google.appengine.api import urlfetch, files, images
from urlparse import urlparse, parse_qs
from models import Bookmarks
from util import send_bm, mys_on, mys_off
from HTMLParser import HTMLParser


def submit_bm(feed, user, title, url, comment):
    bm = Bookmarks()
    result = urlfetch.fetch(url=url, follow_redirects=True, allow_truncated=True, deadline=60)
    if result.status_code == 200 and result.final_url:
        a = result.final_url
    else:
        a = url
    b = a.lstrip().rstrip()
    c = b.split('?utm_source')[0]
    url_candidate = c.split('&feature')[0]
    bmq = Bookmarks.query(Bookmarks.user == user, Bookmarks.url == url_candidate)
    if bmq.get():
        tag_list = []
        for bm in bmq:
            for t in bm.tags:
                if t not in tag_list:
                    tag_list.append(t)
                    bm.tags = tag_list
        ndb.delete_multi([bm.key for bm in bmq])

    url_parsed = urlparse(url_candidate)
    query = parse_qs(url_parsed.query)
    name = url_parsed.path.split('/')[-1]
    ext = name.split('.')[-1].lower()

    if title == '':
        bm.title = name
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

    elif ext in ['jpg', 'png', 'jpeg']:
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

    try:
        if bm.feed.get().notify == 'email':
            deferred.defer(send_bm, bm.key, _queue="emails")
    except:
        if bm.ha_mys:
            deferred.defer(send_bm, bm.key, _queue="emails")


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


def delicious(blob_key, user):
    blob_reader = blobstore.BlobReader(blob_key, buffer_size=1048576)
    parser = BookmarkParser()
    parser.feed(blob_reader.read())
    parser.close()

    was = mys_off(user)
    for bm in parser.bookmarks:
        f = None
        u = user
        t = bm['title']
        o = bm['url']
        c = bm['comment']
        deferred.defer(submit_bm, f, u, t, o, c, _queue="delicious")
    if was == 'was_true':
        deferred.defer(mys_on, user, _queue="delicious")


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
