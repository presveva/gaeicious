#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
from google.appengine.api import search


class UserInfo(ndb.Expando):
    user = ndb.UserProperty()
    email = ndb.ComputedProperty(lambda self: self.user.email())
    mys = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    delicious = ndb.BlobKeyProperty()


class Feeds(ndb.Expando):
    user = ndb.UserProperty()
    feed = ndb.StringProperty()
    title = ndb.StringProperty()
    link = ndb.StringProperty(indexed=False)
    data = ndb.DateTimeProperty(auto_now=True)
    notify = ndb.StringProperty(choices=['web', 'email', 'digest'], default="web")
    last_id = ndb.StringProperty()

    @property
    def id(self):
        return self.key.id()


class Bookmarks(ndb.Expando):
    user = ndb.UserProperty(required=True)
    url = ndb.StringProperty(required=True)
    title = ndb.StringProperty(indexed=False)
    comment = ndb.TextProperty(indexed=False)
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

    @classmethod
    def index_bm(cls, key):
        bm = key.get()
        index = search.Index(name=str(bm.user.user_id()))
        doc = search.Document(doc_id=str(bm.id),
                              fields=[
                              search.TextField(name='url', value=bm.url),
                              search.TextField(name='title', value=bm.title),
                              search.HtmlField(name='comment', value=bm.comment)
                              ])
        try:
            index.put(doc)
        except search.Error:
            pass
