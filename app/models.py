#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.ext import ndb
from google.appengine.api import search


class UserInfo(ndb.Expando):
    access_k = ndb.StringProperty()
    access_s = ndb.StringProperty()
    db_key = ndb.StringProperty()
    db_secret = ndb.StringProperty()
    email = ndb.StringProperty()
    tweets = ndb.BooleanProperty(default=False)
    mys = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    data = ndb.DateTimeProperty(auto_now=True)
    delicious = ndb.BlobKeyProperty()


class Feeds(ndb.Model):
    ui = ndb.KeyProperty(kind=UserInfo)
    feed = ndb.StringProperty()
    title = ndb.StringProperty()
    link = ndb.StringProperty(indexed=False)
    data = ndb.DateTimeProperty(auto_now=True)
    notify = ndb.StringProperty(choices=['web', 'email', 'digest'], default="web")
    last_id = ndb.StringProperty()


class Following(ndb.Model):
    data = ndb.DateTimeProperty(auto_now=True)
    last_id = ndb.StringProperty()


class Bookmarks(ndb.Model):
    title = ndb.StringProperty(indexed=False)
    comment = ndb.TextProperty(indexed=False)
    stato = ndb.StringProperty(
        choices=['inbox', 'trash', 'archive', 'share', 'star', 'delete'], default="inbox")
    data = ndb.DateTimeProperty(auto_now=True)
    feed = ndb.KeyProperty(kind=Feeds)
    domain = ndb.StringProperty()  # 'screen_name' for tweets

    @classmethod
    def userbmq(cls, ui_key, stato):
        return cls.query(cls.stato == stato, ancestor=ui_key).order(-cls.data)

    @classmethod
    def _pre_delete_hook(cls, key):
        index = search.Index(name=key.parent().id())
        try:
            index.delete(key.urlsafe())
        except ValueError:
            pass

    def _post_put_hook(self, future):
        # if self.stato not in ['trash', 'inbox']:
        index = search.Index(name=self.key.parent().string_id())
        doc = search.Document(doc_id=self.key.urlsafe(), fields=[
            search.TextField(name='url', value=self.key.string_id()),
            search.TextField(name='title', value=self.title),
            search.HtmlField(name='comment', value=self.comment)])
        try:
            index.put(doc)
        except search.Error:
            pass
