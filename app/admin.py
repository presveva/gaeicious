#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from . import util
from webapp2 import RequestHandler
from google.appengine.ext.deferred import defer
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from .models import Feeds, Bookmarks, UserInfo, Following


class AdminPage(RequestHandler):

    def get(self):
        from google.appengine.api import users
        continue_url = self.request.get('continue')
        is_admin = users.is_current_user_admin()
        if users.get_current_user():
            url = users.create_logout_url(continue_url)
            text = 'Admin logout'
        else:
            url = users.create_login_url(continue_url)
            text = 'Admin login'
        template = util.env.get_template('admin.html')
        values = {'brand': util.brand, 'text': text, 'url': url, 'admin': is_admin}

        # qry = Bookmarks.query()
        # a, b, c = 0, 0, 0
        # for ent in qry.iter():
            # if hasattr(ent, 'trashed'):
            # if ent.stato not in ['archive', 'trash', 'share', 'inbox', 'star']:
                # a += 1
            # elif key.string_id() is not None:
                # b += 1
            # else:
                # c += 1
        # values.update({'a': a, 'b': b, 'c': c})

        self.response.write(template.render(values))


# CHECK FEEDS
class CheckFeeds(RequestHandler):

    def get(self):
        for feedk in Feeds.query().fetch(keys_only=True):
            defer(check_feed, feedk, _queue='check')
        for foolk in Following.query().fetch(keys_only=True):
            defer(check_following, foolk, _queue='check')


def check_feed(feedk, e=0):
    feed = feedk.get()
    parsed = util.fetch_feed(feed.feed)
    n = len(parsed['items']) if parsed is not False else 0
    if n > 0 and feed.last_id != parsed['items'][0]['link']:
        entry = parsed['items'][e]
        while feed.last_id != entry['link'] and e < (n - 1):
            defer(util.submit_bm, feedk=feedk, uik=feed.ui,
                  title=entry['title'], url=entry['link'],
                  comment=util.build_comment(entry),
                  _queue='submit')
            e += 1
            entry = parsed['items'][e]
        feed.last_id = parsed['items'][0]['link']
        feed.put()
        defer(feed_digest, feedk, _queue='email', _countdown=300)


def check_following(follk, e=0):
    ui = UserInfo.get_by_id(follk.parent().id())
    api = util.get_api(ui.key)
    tweets = api.user_timeline(screen_name=follk.id())
    while tweets[e].id_str != ui.last_id and e < 15:
        Bookmarks.get_or_insert(
            tweets[e].id_str, parent=ui.key, title=tweets[e].user.screen_name,
            domain=tweets[e].user.screen_name, comment=tweets[e].text)
        e += 1
    foll = follk.get()
    foll.last_id = tweets[0].id_str
    foll.put()


def feed_digest(feedk):
    from google.appengine.ext.ndb import put_multi
    from google.appengine.api.mail import send_mail
    bmq = Bookmarks.query(Bookmarks.feed == feedk, Bookmarks.stato == 'inbox')
    feed = feedk.get()
    email = feed.ui.get().email
    if feed.notify == 'digest' and email is not None and bmq.count() > 4:
        title = '[%s] Digest for %s' % (util.brand, feed.title)
        template = util.env.get_template('digest.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.brand
        send_mail(sender=sender, subject=title,
                  to=email, body=html, html=html)
        queue = []
        for bm in bmq:
            bm.stato = 'trash'
            queue.append(bm)
        put_multi(queue)


# 6 HOURS DIGEST
class Activity(RequestHandler):

    def get(self):
        for ui in UserInfo.query():
            defer(cron_trash, ui.key, _queue='worker')
            if ui.daily is True:
                defer(activity_digest, ui.key, _queue='worker')


def activity_digest(uik):
    from google.appengine.api.mail import send_mail
    from datetime import datetime
    bmq = Bookmarks.query(Bookmarks.stato == 'inbox',
                          Bookmarks.data > util.hours_ago(6),
                          ancestor=uik)
    email = uik.get().email
    if bmq.get() is not None and email is not None:
        title = '[%s] Last 6 hours inbox: %s' % (util.brand, util.dtf(datetime.now()))
        template = util.env.get_template('digest.html')
        html = template.render({'bmq': bmq, 'title': title})
        sender = 'bm@%s.appspotmail.com' % util.brand
        send_mail(sender=sender, subject=title,
                  to=email, body=html, html=html)


def cron_trash(uik):
    from google.appengine.ext.ndb import delete_multi
    bmq = Bookmarks.query(Bookmarks.data < util.hours_ago(72),
                          Bookmarks.stato == 'trash',
                          ancestor=uik).fetch(100, keys_only=True)
    delete_multi(bmq)


# ITERATOR
class Iterator(RequestHandler):

    def post(self):
        model = str(self.request.get('model'))
        itera(model)
        self.redirect('/admin/')


def itera(model, cursor=None, count=0):
    from google.appengine.ext.ndb import gql
    qry = gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(50, start_cursor=cursor)
    for ent in res:
        if hasattr(ent, 'archived'):
            defer(make_some, ent, _queue='upgrade')
            count += 1
        # else:
            # defer(make_some, ent, _queue='upgrade')
            # count += 1
    if more and count < 25:
        defer(itera, model, cur, _queue='upgrade')
    elif more:
        defer(itera, model, cur, _queue='upgrade', _countdown=1800)


def make_some(ent):
    if hasattr(ent, 'trashed'):
        delattr(ent, 'trashed')
    if hasattr(ent, 'shared'):
        delattr(ent, 'shared')
    if hasattr(ent, 'starred'):
        delattr(ent, 'starred')
    if hasattr(ent, 'archived'):
        delattr(ent, 'archived')
    if hasattr(ent, 'ui'):
        delattr(ent, 'ui')
    if hasattr(ent, 'url'):
        delattr(ent, 'url')
    ent.put()
    # Bookmarks.get_or_insert(ent.url, parent=ent.ui, feed=ent.feed,
    #                         title=ent.title, comment=ent.comment,
    #                         domain=ent.domain, stato=stato)
    # ent.key.delete()


# DELETE SEARCH INDEX
class DeleteIndex(RequestHandler):

    def post(self):
        index_name = self.request.get('index_name')
        self.reset_index(index_name)
        self.redirect(self.request.referer)

    def reset_index(self, index_name):
        """Delete all the docs in the given index."""

        from google.appengine.api.search import Index
        doc_index = Index(name=index_name)

        while True:
            document_ids = [document.doc_id
                            for document in doc_index.get_range(ids_only=True)]
            if not document_ids:
                break
            doc_index.delete(document_ids)
        doc_index.delete_schema()


# REINDEX ALL BMS
class reindex_all(RequestHandler):

    def get(self):
        defer(reindex)
        self.redirect('/admin')


def reindex(cursor=None):
    bmq = Bookmarks.query()  # .fetch(keys_only=True)
    bms, cur, more = bmq.fetch_page(100, start_cursor=cursor)
    for bm in bms:
        defer(index_bm, bm, _queue='upgrade')
    if more:
        defer(reindex, cur, _queue='upgrade', _countdown=60)


def index_bm(bm):
    from google.appengine.api import search
    index = search.Index(name=bm.key.parent().string_id())
    doc = search.Document(doc_id=bm.key.urlsafe(), fields=[
        search.TextField(name='url', value=bm.key.string_id()),
        search.TextField(name='title', value=bm.title),
        search.HtmlField(name='comment', value=bm.comment)])
    try:
        index.put(doc)
    except search.Error:
        pass


# DELATTR
class del_attr(RequestHandler):

    """Delete property unused after a schema update"""

    def post(self):
        model = str(self.request.get('model'))
        prop = str(self.request.get('prop'))
        iter_entity(model, prop)
        self.redirect('/admin')


def iter_entity(model, prop, cursor=None, count=0):
    from google.appengine.ext.ndb import gql
    qry = gql("SELECT * FROM %s" % model)
    res, cur, more = qry.fetch_page(100, start_cursor=cursor)
    for ent in res:
        if hasattr(ent, prop):
            defer(delatt, ent, prop, _queue='upgrade')
            count += 1
    if more and count < 30:
        defer(iter_entity, model, prop, cur, _queue='upgrade')
    elif more:
        defer(iter_entity, model, prop, cur, _queue='upgrade',
              _countdown=600)


def delatt(ent, prop):
    delattr(ent, prop)
    ent.put()


class PostViaEmail(InboundMailHandler):

    def receive(self, message):
        email = message.sender.split('<')[1].split('>')[0]
        url = message.bodies('text/plain').next()[1].decode().strip()
        ui = UserInfo.query(UserInfo.email == email).get()
        defer(util.submit_bm, feedk=None, uik=ui.key,
              title=message.subject, comment='Sent via email',
              url=url, _queue='submit')


from webapp2 import WSGIApplication, Route
from webapp2_extras.routes import RedirectRoute, PathPrefixRoute
app = WSGIApplication([
    RedirectRoute('/admin/', AdminPage, name='Admin', strict_slash=True),
    Route('/_ah/mail/post@.*', PostViaEmail),
    Route('/_ah/login_required', AdminPage),
    PathPrefixRoute('/admin', [
        Route('/activity', Activity),
        Route('/check', CheckFeeds),
        Route('/del_attr', del_attr),
        Route('/delete_index', DeleteIndex),
        Route('/reindex_all', reindex_all),
        Route('/iterator', Iterator),
    ])], debug=util.debug)
