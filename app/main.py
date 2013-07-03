#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import tweepy
import webapp2
from webapp2_extras import json
from google.appengine.api import search, users
from google.appengine.ext import ndb, deferred
from . import util, secret
from models import UserInfo, Bookmarks, Feeds
from admin import check_feed

auth = tweepy.OAuthHandler(secret.consumer_token,
                           secret.consumer_secret)


class BaseHandler(webapp2.RequestHandler):

    @property
    def ui(self):
        screen_name = self.request.cookies.get('screen_name')
        if screen_name:
            return UserInfo.get_by_id(screen_name)

    def render(self, _template, _values):
        template = util.jinja_environment.get_template(_template)
        return template.render(_values)

    def send_json(self, _values):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.encode(_values))

    def generate(self, template_name, template_values={}):
        is_admin = users.is_current_user_admin()
        values = {'brand': util.brand, 'ui': self.ui, 'admin': is_admin}
        values.update(template_values)
        template = util.jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class HomePage(BaseHandler):

    def get(self):
        oauth_verifier = self.request.get("oauth_verifier")
        if self.ui is not None:
            auth.set_access_token(self.ui.access_k, self.ui.access_s)
            api = tweepy.API(auth)
            self.response.set_cookie('cursor', '')
            self.response.set_cookie('stato', 'inbox')
            self.generate('home.html', {'is_gae': True})
        elif oauth_verifier:
            auth.get_access_token(oauth_verifier)
            api = tweepy.API(auth)
            screen_name = api.me().screen_name

            UserInfo.get_or_insert(
                screen_name, access_k=auth.access_token.key, access_s=auth.access_token.secret)
            self.response.set_cookie('screen_name', screen_name, max_age=604800)
            self.redirect('/')
        else:
            redirect_url = auth.get_authorization_url()
            self.generate('just.html', {'redirect_url': redirect_url})


class Main_Frame(BaseHandler):

    @util.login_required
    def get(self, stato):
        bmq = self.bmq(stato)
        start_cursor = ndb.Cursor(urlsafe=self.request.get('cursor'))
        bms, cur, more = bmq.fetch_page(10, start_cursor=start_cursor)
        cursor = cur.urlsafe() if more else ''
        tmpl = 'stream.html' if stato == 'stream' else 'frame.html'
        html = self.render(tmpl, {'bms': bms, 'cursor': cursor})
        self.response.set_cookie('stato', stato)
        self.response.write(html)

    def bmq(self, stato):
        if stato == 'domain':
            domain = self.request.get('domain')
            bmq = Bookmarks.query(Bookmarks.domain == domain, ancestor=self.ui.key)
        elif stato == 'stream':
            bmq = Bookmarks.query(Bookmarks.stato == 'share')
        else:
            bmq = Bookmarks.userbmq(self.ui.key, stato)
        return bmq


class Logout(BaseHandler):

    def get(self):
        self.response.set_cookie('screen_name', '')
        self.redirect('/')


class SettingPage(BaseHandler):

    @util.login_required
    def get(self):
        bookmarklet = "javascript:location.href='" + \
            self.request.host_url + "/submit?" + \
            "url='+encodeURIComponent(location.href)+'" + \
            "&title='+encodeURIComponent(document.title)+'" + \
            "'+'&comment='+document.getSelection().toString()"
        self.response.set_cookie('mys', '%s' % self.ui.mys)
        self.response.set_cookie('daily', '%s' % self.ui.daily)
        self.response.set_cookie('stato', 'setting')
        self.generate(
            'setting.html', {'bookmarklet': bookmarklet,
                             'upload_url': util.upload_url})


class FeedsPage(BaseHandler):

    @util.login_required
    def get(self):
        feed_list = Feeds.query(Feeds.ui == self.ui.key).order(Feeds.title)
        self.response.set_cookie('stato', 'feeds')
        self.generate('feeds.html', {'feeds': feed_list})

    @util.login_required
    def delete(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()
        # self.redirect(self.request.referer)

    @util.login_required
    def post(self):
        from libs.feedparser import parse
        feed = self.request.get('url')
        q = Feeds.query(Feeds.ui == self.ui.key, Feeds.feed == feed)
        if q.get() is None:
            d = parse(str(feed))
            feed_k = Feeds(ui=self.ui.key, feed=feed,
                           title=d['channel']['title'],
                           link=d['channel']['link'],
                           last_id=d['items'][2]['link']).put()
            deferred.defer(check_feed, feed_k, _queue='check')
        self.redirect('/feeds')


class ArchiveBM(BaseHandler):

    @util.login_required
    def get(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            if bm.stato == 'inbox':
                bm.stato = 'archive'
            else:
                bm.stato = 'inbox'
            bm.put()


class TrashBM(BaseHandler):

    @util.login_required
    def get(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            if bm.stato == 'trash':
                bm.key.delete()
            else:
                bm.stato = 'trash'
                bm.put()


class ShareBM(BaseHandler):

    @util.login_required
    def get(self, us):

        bm = ndb.Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            if bm.stato == 'share':
                bm.stato = 'inbox'
                eye = '<i class="icon-eye-close"></i>'
                btn = ''
            else:
                bm.stato = 'share'
                eye = '<i class="icon-eye-open"></i>'
                btn = '<a class="btn btn-small btn-link" href="/bm/' + \
                    us + '" target="_blank">link</a>'
            bm.put()
            self.send_json({"eye": eye, "btn": btn})


class StarBM(BaseHandler):

    @util.login_required
    def get(self, us):

        bm = ndb.Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            if bm.stato == 'star':
                bm.stato = 'archive'
            else:
                bm.stato = 'star'
            bm.put()


class empty_trash(BaseHandler):

    @util.login_required
    def get(self):
        deferred.defer(util.delete_bms, self.ui.key)
        self.redirect(self.request.referer)


class ItemPage(BaseHandler):

    def get(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        if bm.stato == 'share':
            self.generate('item.html', {'bm': bm})
        else:
            self.redirect('/')

    @util.login_required
    def post(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            bm.title = self.request.get('title').encode('utf8')
            bm.comment = self.request.get('comment').encode('utf8')
            bm.put()
            self.response.write("<td>%s</td>" % bm.comment)


class cerca(BaseHandler):

    @util.login_required
    def post(self):
        query_string = self.request.get('query_string')
        try:
            results = search.Index(name=self.ui.key.string_id()).search(query_string)
            bms_us = [str(doc.doc_id) for doc in results]
            keys = [ndb.Key(urlsafe=str(us)) for us in bms_us]
            if len(keys) > 0:
                bms = ndb.get_multi(keys)
                html = self.render('frame.html', {'bms': bms})
                self.response.set_cookie('cursor', '')
                self.response.write(html)
        except search.Error:
            pass


class GetEdit(webapp2.RequestHandler):

    def get(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        self.render('edit.html', {'bm': bm})


class CheckFeed(webapp2.RequestHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(
            check_feed, feed.key, _queue='check')


class SetMys(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
        if ui.mys is False:
            ui.mys = True
            html = '<i class="icon-thumbs-up"></i> <b>Enabled </b>'
        else:
            ui.mys = False
            html = '<i class="icon-thumbs-down"></i> <b>Disabled</b>'
        ui.put()
        self.response.write(html)


class SetDaily(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
        if ui.daily is False:
            ui.daily = True
            html = '<i class="icon-thumbs-up"></i> <b>Enabled </b>'
        else:
            ui.daily = False
            html = '<i class="icon-thumbs-down"></i> <b>Disabled</b>'
        ui.put()
        self.response.write(html)


class SetNotify(webapp2.RequestHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        feed.notify = self.request.get('notify')
        feed.put()


class SaveEmail(BaseHandler):

    @util.login_required
    def post(self):
        ui = self.ui
        ui.email = self.request.get('email')
        ui.put()
        self.redirect(self.request.referer)


class AddBM(BaseHandler):

    @util.login_required
    def get(self):
        util.submit_bm(feedk=None,
                       uik=self.ui.key,
                       title=self.request.get('title'),
                       url=self.request.get('url'),
                       comment=self.request.get('comment'))
        self.redirect('/')


class CopyBM(BaseHandler):

    @util.login_required
    def get(self, us):
        bm = ndb.Key(urlsafe=str(us)).get()
        deferred.defer(util.submit_bm, feedk=None, uik=self.ui.key,
                       title=bm.title, url=bm.key.id(), comment=bm.comment)

app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/logout', Logout),
    ('/search', cerca),
    (r'/bms/(.*)', Main_Frame),
    ('/submit', AddBM),
    (r'/copy/(.*)', CopyBM),
    ('/checkfeed', CheckFeed),
    (r'/archive/(.*)', ArchiveBM),
    (r'/trash/(.*)', TrashBM),
    ('/empty_trash', empty_trash),
    ('/setting', SettingPage),
    ('/feeds', FeedsPage),
    ('/setmys', SetMys),
    ('/setdaily', SetDaily),
    ('/setnotify', SetNotify),
    (r'/share/(.*)', ShareBM),
    (r'/star/(.*)', StarBM),
    ('/save_email', SaveEmail),
    (r'/getedit/(.*)', GetEdit),
    (r'/bm/(.*)', ItemPage),
    ('/upload', util.UploadDelicious),
], debug=util.debug, config=util.config)

if __name__ == "__main__":
    app.run()
