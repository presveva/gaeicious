#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
from webapp2 import RequestHandler
from google.appengine.api import users
from models import Bookmarks, UserInfo, Feeds, Tags

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates', 'partials']))


class GetComment(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.response.write(bm.comment)


class GetTagsFeed(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        template = jinja_environment.get_template('gettagsfeed.html')
        values = {'feed': feed}
        other_tags = template.render(values)
        self.response.write(other_tags)


class GetTags(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        template = jinja_environment.get_template('other_tags.html')
        values = {'bm': bm}
        other_tags = template.render(values)
        self.response.write(other_tags)


class GetEdit(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        template = jinja_environment.get_template('edit.html')
        values = {'bm': bm}
        html_page = template.render(values)
        self.response.write(html_page)


class gettagcloud(RequestHandler):
    def get(self):
        q = Tags.query(Tags.user == users.get_current_user())
        q = q.order(Tags.name)
        template = jinja_environment.get_template('tagcloud.html')
        values = {'q': q}
        html = template.render(values)
        self.response.set_cookie('active-tab', 'tagcloud')
        self.response.write(html)


class get_tips(RequestHandler):
    def get(self):
        template = jinja_environment.get_template('tips.html')
        html = template.render({})
        self.response.write(html)


class get_empty_trash(RequestHandler):
    def get(self):
        template = jinja_environment.get_template('empty_trash.html')
        html = template.render({})
        self.response.write(html)


class StarBM(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            if bm.starred == False:
                bm.starred = True
                html = '<i class="icon-star"></i>'
            else:
                bm.starred = False
                html = '<i class="icon-star-empty"></i>'
            bm.put()
        self.response.write(html)


class ShareBM(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('id')))
        if users.get_current_user() == bm.user:
            if bm.shared == False:
                bm.shared = True
                eye = '<i class="icon-eye-open"></i>'
            else:
                bm.shared = False
                eye = '<i class="icon-eye-close"></i>'
            bm.put()
        self.response.write(eye)


class AddTag(RequestHandler):
    def get(self):
        user = users.get_current_user()
        tag_str = self.request.get('tag')
        if user:
            tag = Tags.query(Tags.user == user, Tags.name == tag_str).get()
            if tag is None:
                newtag = Tags()
                newtag.name = tag_str
                newtag.user = user
            else:
                newtag = tag
            newtag.put()


class AssignTag(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        tag = Tags.get_by_id(int(self.request.get('tag')))
        # if users.get_current_user() == bm.user:
        bm.tags.append(tag.key)
        bm.put()
        template = jinja_environment.get_template('tags.html')
        values = {'bm': bm}
        html = template.render(values)
        self.response.write(html)


class RemoveTag(RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        tag = Tags.get_by_id(int(self.request.get('tag')))
        # if users.get_current_user() == bm.user:
        bm.tags.remove(tag.key)
        bm.put()
        template = jinja_environment.get_template('tags.html')
        values = {'bm': bm}
        html = template.render(values)
        self.response.write(html)


class get_refine_tags(RequestHandler):
    def get(self):
        from util import tag_set
        arg1 = self.request.get('arg1')
        q1 = Bookmarks.query(Bookmarks.user == users.get_current_user())
        q2 = q1.order(-Bookmarks.data)
        t1 = Tags.query(Tags.user == users.get_current_user())
        tag1 = t1.filter(Tags.name == arg1).get()
        bmq = q2.filter(Bookmarks.tags == tag1.key)
        tagset = tag_set(bmq)
        tagset.remove(tag1.key)
        template = jinja_environment.get_template('tagset.html')
        html = template.render({'tagset': tagset, 'arg1': arg1})
        self.response.write(html)

###################################################
## Setting page
###################################################


class SetMys(RequestHandler):
    def get(self):
        ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
        if ui.mys == False:
            ui.mys = True
            html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
        else:
            ui.mys = False
            html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
        ui.put()
        self.response.write(html)


class SetDaily(RequestHandler):
    def get(self):
        ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
        if ui.daily == False:
            ui.daily = True
            html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
        else:
            ui.daily = False
            html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
        ui.put()
        self.response.write(html)


class SetTwitt(RequestHandler):
    def get(self):
        ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
        if ui.twitt == False:
            ui.twitt = True
            html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
        else:
            ui.twitt = False
            html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
        ui.put()
        self.response.write(html)


class SetNotify(RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        feed.notify = self.request.get('notify')
        feed.put()
