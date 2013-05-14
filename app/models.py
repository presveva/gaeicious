#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb, deferred
from google.appengine.api import search


class UserInfo(ndb.Expando):
    access_k = ndb.StringProperty()
    access_s = ndb.StringProperty()
    email = ndb.StringProperty()
    last_id = ndb.StringProperty()
    data = ndb.DateTimeProperty(auto_now=True)
    mys = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    delicious = ndb.BlobKeyProperty()

    def followers_ids(self):
        followers = Followers.query(Followers.ui == self.key).fetch()
        return [follower.user_id for follower in followers]

    def new_foll(self):
        return Followers.query(Followers.ui == self.key,
                               Followers.new == True).fetch(keys_only=True)

    def lost_foll(self):
        return Followers.query(Followers.ui == self.key,
                               Followers.lost == True).fetch(keys_only=True)


class Followers(ndb.Model):
    ui = ndb.KeyProperty(kind=UserInfo)
    user_id = ndb.IntegerProperty()
    screen_name = ndb.StringProperty()
    data = ndb.DateTimeProperty(auto_now=True)
    new = ndb.BooleanProperty(default=False)
    lost = ndb.BooleanProperty(default=False)


class Feeds(ndb.Expando):
    ui = ndb.KeyProperty(kind=UserInfo)
    feed = ndb.StringProperty()
    title = ndb.StringProperty()
    link = ndb.StringProperty(indexed=False)
    data = ndb.DateTimeProperty(auto_now=True)
    notify = ndb.StringProperty(choices=[
                                'web', 'email', 'digest'], default="web")
    last_id = ndb.StringProperty()

    @property
    def id(self):
        return self.key.id()


class Bookmarks(ndb.Expando):
    ui = ndb.KeyProperty(kind=UserInfo)
    url = ndb.StringProperty()
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
        index = search.Index(name=bm.ui.id())
        index.delete(str(bm.key.id()))

    def _post_put_hook(self, future):
        index = search.Index(name=str(self.ui.id()))
        doc = search.Document(doc_id=str(self.key.id()),
                              fields=[
                              search.TextField(name='url', value=self.url),
                              search.TextField(name='title', value=self.title),
                              search.HtmlField(
                                  name='comment', value=self.comment)
                              ])
        try:
            index.put(doc)
        except search.Error:
            pass
