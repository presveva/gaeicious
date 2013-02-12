#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
from google.appengine.api import search


class UserInfo(ndb.Expando):
    user = ndb.UserProperty()
    email = ndb.ComputedProperty(lambda self: self.user.email())
    user_id = ndb.ComputedProperty(lambda self: self.user.user_id())
    data = ndb.DateTimeProperty(auto_now=True)
    mys = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    delicious = ndb.BlobKeyProperty()


class Feeds(ndb.Expando):
    user = ndb.UserProperty()
    data = ndb.DateTimeProperty(auto_now=True)
    feed = ndb.StringProperty()  # url
    blog = ndb.StringProperty(indexed=False)  # feed.title
    root = ndb.StringProperty(indexed=False)  # feed.link
    notify = ndb.StringProperty(choices=['web', 'email', 'digest'], default="web")
    url = ndb.StringProperty()  # link

    @property
    def id(self):
        return self.key.id()


class Bookmarks(ndb.Expando):
    user = ndb.UserProperty(required=True)
    url = ndb.StringProperty(required=True)
    title = ndb.StringProperty(indexed=False)
    comment = ndb.TextProperty(indexed=False)
    blob_key = ndb.BlobKeyProperty(indexed=False)
    archived = ndb.BooleanProperty(default=False)
    starred = ndb.BooleanProperty(default=False)
    shared = ndb.BooleanProperty(default=False)
    trashed = ndb.BooleanProperty(default=False)
    data = ndb.DateTimeProperty(auto_now=True)
    feed = ndb.KeyProperty(kind=Feeds)
    domain = ndb.StringProperty()

    @property
    def id(self):
        return self.key.id()

    @classmethod
    def _pre_delete_hook(cls, key):
        bm = key.get()
        index = search.Index(name=bm.user.user_id())
        index.remove(str(bm.id))
