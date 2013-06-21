#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
from google.appengine.api import search


class UserInfo(ndb.Model):
    access_k = ndb.StringProperty()
    access_s = ndb.StringProperty()
    email = ndb.StringProperty()
    last_id = ndb.StringProperty()
    data = ndb.DateTimeProperty(auto_now=True)
    mys = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    delicious = ndb.BlobKeyProperty()


class Feeds(ndb.Model):
    ui = ndb.KeyProperty(kind=UserInfo)
    feed = ndb.StringProperty()
    title = ndb.StringProperty()
    link = ndb.StringProperty(indexed=False)
    data = ndb.DateTimeProperty(auto_now=True)
    notify = ndb.StringProperty(choices=['web', 'email', 'digest'],
                                default="web")
    last_id = ndb.StringProperty()


class Bookmarks(ndb.Expando):
    title = ndb.StringProperty(indexed=False)
    comment = ndb.TextProperty(indexed=False)
    stato = ndb.StringProperty(
        choices=['inbox', 'trash', 'archive', 'share', 'star'],
        default="inbox")
    data = ndb.DateTimeProperty(auto_now=True)
    feed = ndb.KeyProperty(kind=Feeds)
    domain = ndb.StringProperty()

    @classmethod
    def _pre_delete_hook(cls, key):
        bm = key.get()
        index = search.Index(name=bm.key.parent().id())
        index.delete(bm.key.string_id())

    def _post_put_hook(self, future):
        Bookmarks.index_bm(self.key)

    @classmethod
    def index_bm(cls, key):
        bm = key.get()
        index = search.Index(name=bm.key.parent().string_id())
        doc = search.Document(doc_id=bm.key.urlsafe(), fields=[
                              search.TextField(
                              name='url', value=bm.key.string_id()),
                              search.TextField(
                              name='title', value=bm.title),
                              search.HtmlField(
                              name='comment', value=bm.comment)
                              ])
        try:
            index.put(doc)
        except search.Error:
            pass
