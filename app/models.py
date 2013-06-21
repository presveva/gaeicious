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
    # ui = ndb.KeyProperty(kind=UserInfo)  # parent()
    # url = ndb.StringProperty()  # id()
    # archived = ndb.BooleanProperty(default=False)
    # trashed = ndb.BooleanProperty(default=False)
    # starred = ndb.BooleanProperty(default=False)
    # shared = ndb.BooleanProperty(default=False)  # todo new model Shared

    # @property
    # def share(self):
    #     qry = Shared.query(Shared.bm == self.key)
    #     if qry.get():
    #         return qry.get().key.id()

    # @classmethod
    # def _pre_delete_hook(cls, key):
    #     bm = key.get()
    #     index = search.Index(name=bm.key.parent().id())
    #     index.delete(str(bm.key.id()))

    # def _post_put_hook(self, future):
    #     index = search.Index(name=str(self.ui.id()))
    #     doc = search.Document(doc_id=str(self.key.urlsafe()),
    #                           fields=[
    #                           search.TextField(
    #                               name='url', value=self.key.id()),
    #                           search.TextField(name='title', value=self.title),
    #                           search.HtmlField(
    #                               name='comment', value=self.comment)
    #                           ])
    #     try:
    #         index.put(doc)
    #     except search.Error:
    #         pass


# class Shared(ndb.Model):
# ui = ndb.KeyProperty(kind=UserInfo)  # parent()
# bm = ndb.KeyProperty(kind=Bookmarks)  # parent()
#     data = ndb.DateTimeProperty(auto_now=True)




# class Starred(ndb.Model):
# ui = ndb.KeyProperty(kind=UserInfo)  # parent()
# bm = ndb.KeyProperty(kind=Bookmarks)  # parent()
