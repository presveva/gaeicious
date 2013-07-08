#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from . import util
from webapp2 import RequestHandler, WSGIApplication
from google.appengine.ext.deferred import defer
from google.appengine.ext.ndb import Key
from .models import Feeds, Following
from .admin import check_feed, check_following


class BaseHandler(RequestHandler):

    @property
    def ui(self):
        from .models import UserInfo
        screen_name = self.request.cookies.get('screen_name')
        if screen_name:
            return UserInfo.get_by_id(screen_name)

    def render(self, _template, _values):
        template = util.env.get_template(_template)
        return template.render(_values)

    def send_json(self, _values):
        from webapp2_extras import json
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.encode(_values))

    def generate(self, template_name, template_values={}):
        from google.appengine.api import users
        is_admin = users.is_current_user_admin()
        values = {'brand': util.brand, 'ui': self.ui, 'admin': is_admin}
        values.update(template_values)
        template = util.env.get_template(template_name)
        self.response.write(template.render(values))


class HomePage(BaseHandler):

    def get(self):
        from .models import UserInfo
        oauth_verifier = self.request.get("oauth_verifier")
        if self.ui is not None:
            util.auth.set_access_token(self.ui.access_k, self.ui.access_s)
            self.response.set_cookie('cursor', '')
            self.response.set_cookie('stato', 'inbox')
            self.generate('home.html', {'is_gae': True})
        elif oauth_verifier:
            util.auth.get_access_token(oauth_verifier)
            screen_name = util.api.me().screen_name

            UserInfo.get_or_insert(screen_name,
                                   access_k=util.auth.access_token.key,
                                   access_s=util.auth.access_token.secret)

            self.response.set_cookie('screen_name', screen_name, max_age=604800)
            self.redirect('/')
        else:
            redirect_url = util.auth.get_authorization_url()
            self.generate('just.html', {'redirect_url': redirect_url})


class Main_Frame(BaseHandler):

    @util.login_required
    def get(self, stato):
        from .models import Bookmarks
        from google.appengine.ext.ndb import Cursor
        follqry = Following.query().fetch(keys_only=True)
        follows = [f.id() for f in follqry]
        bmq = Bookmarks.userbmq(self.ui.key, stato)
        start_cursor = Cursor(urlsafe=self.request.get('cursor'))
        bms, cur, more = bmq.fetch_page(10, start_cursor=start_cursor)
        cursor = cur.urlsafe() if more else ''
        html = self.render(
            'frame.html', {'bms': bms, 'cursor': cursor, 'follows': follows})
        self.response.set_cookie('stato', stato)
        self.response.write(html)


class SettingPage(BaseHandler):

    @util.login_required
    def get(self):
        oauth_token = self.request.get('oauth_token')

        bookmarklet = "javascript:location.href='" + \
            self.request.host_url + "/submit?" + \
            "url='+encodeURIComponent(location.href)+'" + \
            "&title='+encodeURIComponent(document.title)+'" + \
            "'+'&comment='+document.getSelection().toString()"
        self.response.set_cookie('mys', str(self.ui.mys))
        self.response.set_cookie('daily', str(self.ui.daily))
        self.response.set_cookie('stato', 'setting')
        values = {'bookmarklet': bookmarklet, 'upload_url': util.upload_url}
        if oauth_token:
            access_token = util.sess.obtain_access_token(util.request_token)
            ui = self.ui
            ui.db_key = access_token.key
            ui.db_secret = access_token.secret
            ui.put()
            self.redirect('/setting')
        if not util.sess.is_linked():
            if self.ui.db_key:
                util.sess.set_token(self.ui.db_key, self.ui.db_secret)
            else:
                values.update({'dropbox_url': util.dropbox_url})
        self.generate('setting.html', values)


class FeedsPage(BaseHandler):

    @util.login_required
    def get(self):
        feed_list = Feeds.query(Feeds.ui == self.ui.key).order(Feeds.title)
        self.response.set_cookie('stato', 'feeds')
        self.generate('feeds.html', {'feeds': feed_list})

    @util.login_required
    def post(self):
        from libs.feedparser import parse
        feed = self.request.get('url')
        q = Feeds.query(Feeds.ui == self.ui.key, Feeds.feed == feed)
        if q.get() is None:
            d = parse(str(feed))
            feed_k = Feeds(ui=self.ui.key, feed=feed,
                           title=d.feed.title if 'title' in d.feed else d[
                               'channel']['title'],
                           link=d['channel']['link'],
                           last_id=d['items'][2]['link']).put()
            defer(check_feed, feed_k, _queue='check')
        self.redirect('/feeds')

    @util.login_required
    def delete(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()


class FollowingPage(BaseHandler):

    @util.login_required
    def get(self):
        following = Following.query(ancestor=self.ui.key)
        self.response.set_cookie('stato', 'following')
        self.generate('following.html', {'following': following})

    @util.login_required
    def post(self):
        username = self.request.get('username')
        foll = Following.get_or_insert(username, parent=self.ui.key)
        defer(check_following, foll.key)
        self.redirect('/following')

    @util.login_required
    def delete(self):
        foll = Following.get_by_id(self.request.get('id'), parent=self.ui.key)
        foll.key.delete()


class SaveEmail(BaseHandler):

    @util.login_required
    def post(self):
        ui = self.ui
        ui.email = self.request.get('email')
        ui.put()
        self.redirect(self.request.referer)

    @util.login_required
    def get(self):
        ui = self.ui
        mys = True if ui.mys is False else False
        self.response.set_cookie('mys', str(mys))
        ui.mys = mys
        ui.put()
        # self.response.write(html)

    @util.login_required
    def put(self):
        ui = self.ui
        daily = True if ui.daily is False else False
        self.response.set_cookie('daily', str(daily))
        ui.daily = daily
        ui.put()


class Bookmark(BaseHandler):

    def get(self, us):
        bm = Key(urlsafe=str(us)).get()
        if bm.stato == 'share':
            self.generate('item.html', {'bm': bm})
        else:
            self.redirect('/')

    @util.login_required
    def post(self, us):
        bm = Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            bm.title = self.request.get('title').encode('utf8')
            bm.comment = self.request.get('comment').encode('utf8')
            bm.put()
            self.response.write("<td>%s</td>" % bm.comment)

    @util.login_required
    def put(self, us):
        bm = Key(urlsafe=str(us)).get()
        if self.ui.key == bm.key.parent():
            old, btn = self.request.cookies.get('stato'), self.request.get('btn')
            if btn == 'trash':
                if old == 'trash':
                    bm.key.delete()
                else:
                    bm.stato = 'trash'
            if btn == 'inbox':
                bm.stato = 'archive' if old == 'inbox' else 'inbox'
            if btn == 'star':
                bm.stato = 'archive' if old == 'star' else 'star'
            if btn == 'share':
                bm.stato = 'inbox' if bm.stato == 'share' else 'share'
            bm.put()


class cerca(BaseHandler):

    @util.login_required
    def post(self):

        from google.appengine.ext.ndb import get_multi
        from google.appengine.api.search import Index, Error
        query_string = self.request.get('query_string')
        try:
            results = Index(name=self.ui.key.string_id()).search(query_string)
            bms_us = [str(doc.doc_id) for doc in results]
            keys = [Key(urlsafe=str(us)) for us in bms_us]
            if len(keys) > 0:
                bms = get_multi(keys)
                html = self.render('frame.html', {'bms': bms})
                self.response.set_cookie('cursor', '')
                self.response.write(html)
        except Error:
            pass


class SetNotify(RequestHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        feed.notify = self.request.get('notify')
        feed.put()


class AddBM(BaseHandler):

    @util.login_required
    def get(self):
        util.submit_bm(uik=self.ui.key,
                       title=self.request.get('title'),
                       url=self.request.get('url'),
                       comment=self.request.get('comment'))
        self.redirect('/')


class empty_trash(BaseHandler):

    @util.login_required
    def get(self):
        defer(util.delete_bms, self.ui.key)
        self.redirect(self.request.referer)


class CheckFeed(RequestHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        if feed.data < util.hours_ago(120):
            feed.last_id = ''
            feed.put()
        check_feed(feed.key)


class Logout(BaseHandler):

    def get(self):
        self.response.set_cookie('screen_name', '')
        self.redirect('/')

app = WSGIApplication([
    ('/', HomePage),
    ('/logout', Logout),
    ('/search', cerca),
    (r'/bms/(.*)', Main_Frame),
    ('/submit', AddBM),
    ('/empty_trash', empty_trash),
    ('/setting', SettingPage),
    ('/feeds', FeedsPage),
    ('/following', FollowingPage),
    ('/checkfeed', CheckFeed),
    ('/setnotify', SetNotify),
    ('/save_email', SaveEmail),
    (r'/bm/(.*)', Bookmark),
    ('/upload', util.UploadDelicious),
], debug=util.debug)

if __name__ == "__main__":
    app.run()
