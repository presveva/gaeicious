#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from webapp2 import RequestHandler
from google.appengine.api import users, memcache
from google.appengine.ext import ndb, deferred
from models import Feeds, Bookmarks, Tags, UserInfo
from handlers import utils, parser


class ArchiveBM(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            if bm.trashed:
                bm.archived = False
                bm.trashed = False
            elif bm.archived:
                bm.archived = False
            else:
                bm.archived = True
            bm.put()
        bm_ids_key = 'bm_ids_' + str(users.get_current_user().user_id())
        bm_ids_list = memcache.get(bm_ids_key)
        bm_ids_list.remove(int(self.request.get('bm')))
        memcache.set(bm_ids_key, bm_ids_list)


class TrashBM(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            if bm.trashed == False:
                bm.archived = False
                bm.trashed = True
                bm.put()
            else:
                bm.key.delete()
        bm_ids_key = 'bm_ids_' + str(users.get_current_user().user_id())
        bm_ids_list = memcache.get(bm_ids_key)
        bm_ids_list.remove(int(self.request.get('bm')))
        memcache.set(bm_ids_key, bm_ids_list)


class archive_all(RequestHandler):
    def get(self):
        bm_ids_key = 'bm_ids_' + str(users.get_current_user().user_id())
        bm_ids_list = memcache.get(bm_ids_key)
        queue = []
        for bm_id in bm_ids_list:
            bm = Bookmarks.get_by_id(int(bm_id))
            if bm.archived == False and bm.trashed == False:
                bm.archived = True
                queue.append(bm)
        ndb.put_multi(queue)


class trash_all(RequestHandler):
    def get(self):
        bm_ids_key = 'bm_ids_' + str(users.get_current_user().user_id())
        bm_ids_list = memcache.get(bm_ids_key)
        queue = []
        for bm_id in bm_ids_list:
            bm = Bookmarks.get_by_id(int(bm_id))
            if bm.trashed == False and bm.starred == False:
                bm.trashed = True
                queue.append(bm)
        ndb.put_multi(queue)


class EditBM(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            def txn():
                bm.url = self.request.get('url').encode('utf8')
                bm.title = self.request.get('title').encode('utf8')
                bm.comment = self.request.get('comment').encode('utf8')
                bm.put()
            ndb.transaction(txn)
        self.redirect(self.request.referer)


# class DeleteTag(RequestHandler):
#     def get(self):
#         tag = Tags.get_by_id(int(self.request.get('tag')))
#         if users.get_current_user() == tag.user:
#             bmq = Bookmarks.query(Bookmarks.tags == tag.key)
#             for bm in bmq:
#                 bm.tags.remove(tag.key)
#                 bm.put()
#             tag.key.delete()
#         self.redirect(self.request.referer)


class Empty_Trash(RequestHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.user == users.get_current_user())
        bmq = bmq.filter(Bookmarks.trashed == True)
        ndb.delete_multi([bm.key for bm in bmq])
        self.redirect(self.request.referer)


class AssTagFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            if tag in feed.tags:
                pass
            else:
                feed.tags.append(tag.key)
                feed.put()
        self.redirect(self.request.referer)


class RemoveTagFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            feed.tags.remove(tag.key)
            feed.put()
        self.redirect(self.request.referer)


class CheckFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(parser.pop_feed, feed.key, _target="worker", _queue="admin")


#### admin ###

class CheckFeeds(RequestHandler):
    def get(self):
        for feed in Feeds.query():
            deferred.defer(parser.pop_feed, feed.key, _target="worker", _queue="admin")


class SendDigest(RequestHandler):
    def get(self):
        for feed in Feeds.query():
            if feed.notify == 'digest':
                deferred.defer(util.feed_digest, feed.key, _target="worker", _queue="emails")


class SendActivity(RequestHandler):
    def get(self):
        for ui in UserInfo.query():
            if ui.daily:
                deferred.defer(util.daily_digest, ui.user, _target="worker", _queue="emails")


class del_attr(RequestHandler):
    """delete old property from datastore"""
    def post(self):
        model = self.request.get('model')
        prop = self.request.get('prop')
        q = ndb.gql("SELECT %s FROM %s" % (prop, model))
        for r in q:
            deferred.defer(delatt, r.key, prop, _queue="admin")
        self.redirect('/admin')


def delatt(rkey, prop):
    r = rkey.get()
    delattr(r, '%s' % prop)
    r.put()


#### don't care ###

class Upgrade(RequestHandler):
    """change this handler for admin operations"""
    def get(self):
        for tag in Tags.query():
            tag.put()


def upgrade(itemk):
    for tag in Tags.query():
        tag.put()


class Script(RequestHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.archived == False)
        bmq = bmq.filter(Bookmarks.domain == None)
        for bm in bmq:
            f = None
            u = bm.user
            t = bm.title
            o = bm.url
            c = bm.comment
            deferred.defer(parser.submit_bm, f, u, t, o, c, _target="worker")


def add_url(bmk):
    bm = bmk.get()
    bm.url = bm.original
    bm.put()


def add_domain(bmk):
    bm = bmk.get()
    for t in bm.tags:
        name = t.get().name
        bm.labels.append(name)
        bm.put()
