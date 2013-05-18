#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from . import util
import tweepy
from . import secret
import webapp2
from webapp2_extras import json
from google.appengine.api import app_identity, search, mail
from google.appengine.ext import ndb, blobstore, deferred
from .models import *

auth = tweepy.OAuthHandler(secret.consumer_token,
                           secret.consumer_secret)


class BaseHandler(webapp2.RequestHandler):

    @property
    def admin(self):
        screen_name = self.request.cookies.get('screen_name')
        if screen_name:
            return True if screen_name in secret.admins else False

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
        values = {
            'brand': app_identity.get_application_id(),
            'admin': self.admin,
            'ui': self.ui
        }
        values.update(template_values)
        template = util.jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class HomePage(BaseHandler):

    def get(self):
        oauth_verifier = self.request.get("oauth_verifier")
        if self.ui is not None:
            auth.set_access_token(self.ui.access_k, self.ui.access_s)
            api = tweepy.API(auth)
            self.generate('home.html', {})
        elif oauth_verifier:
            auth.get_access_token(oauth_verifier)
            api = tweepy.API(auth)
            screen_name = api.me().screen_name

            ui = UserInfo.get_or_insert(screen_name)
            ui.access_k = auth.access_token.key
            ui.access_s = auth.access_token.secret
            ui.put()
            self.response.set_cookie('screen_name', screen_name)
            self.redirect('/')
        else:
            redirect_url = auth.get_authorization_url()
            self.generate('just.html', {'redirect_url': redirect_url})


class Main_Frame(BaseHandler):

    @util.login_required
    def get(self, page):
        bmq = self.bmq(page)
        cursor = ndb.Cursor(urlsafe=self.request.get('cursor'))
        self.build(page, bmq, cursor)

    def bmq(self, page):
        q1 = Bookmarks.query(Bookmarks.ui == self.ui.key
                             ).order(-Bookmarks.data)
        q2 = q1.filter(Bookmarks.trashed == False)

        if page == 'archived':
            bmq = q2.filter(Bookmarks.archived == True)
        elif page == 'shared':
            bmq = q2.filter(Bookmarks.shared == True)
        elif page == 'starred':
            bmq = q2.filter(Bookmarks.starred == True)
        elif page == 'trashed':
            bmq = q1.filter(Bookmarks.trashed == True)
        elif page == 'domain':
            bmq = q1.filter(Bookmarks.domain == self.request.get('domain'))
        elif page == 'stream':
            bmq = Bookmarks.query(Bookmarks.trashed == False,
                                  Bookmarks.shared == True
                                  ).order(-Bookmarks.data)
        else:
            bmq = q2.filter(Bookmarks.archived == False)
        return bmq

    def build(self, page, bmq, cursor):
        bms, next_curs, more = bmq.fetch_page(15, start_cursor=cursor)
        next_c = next_curs.urlsafe() if more else None
        if page == 'stream':
            html = self.render('stream.html', {'bms': bms})
        else:
            html = self.render('frame.html', {'bms': bms, 'cursor': next_c})
        more = self.render('more.html', {'cursor': next_c})
        self.response.set_cookie('active-tab', page)
        self.send_json({"html": html, "more": more})


class Logout(BaseHandler):

    def get(self):
        self.response.set_cookie('screen_name', '')
        self.redirect('/')


class ItemPage(BaseHandler):

    def get(self, id):
        bm = Bookmarks.get_by_id(int(id))
        if bm.shared:
            self.generate('item.html', {'bm': bm})
        else:
            self.redirect('/')


class AdminPage(BaseHandler):

    def get(self):
        self.response.set_cookie('active-tab', 'admin')
        self.generate('admin.html')


class SettingPage(BaseHandler):

    @util.login_required
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        brand = app_identity.get_application_id()
        bookmarklet = "javascript:location.href='" + \
            self.request.host_url + "/submit?" + \
            "url='+encodeURIComponent(location.href)+'" + \
            "&title='+encodeURIComponent(document.title)+'" + \
            "&user='+'" + str(self.ui.key.id()) + \
            "'+'&comment='+document.getSelection().toString()"
        self.response.set_cookie('mys', '%s' % self.ui.mys)
        self.response.set_cookie('daily', '%s' % self.ui.daily)
        self.response.set_cookie('active-tab', 'setting')
        self.generate(
            'setting.html', {'bookmarklet': bookmarklet,
                             'upload_url': upload_url, 'brand': brand, })


class FeedsPage(BaseHandler):

    @util.login_required
    def get(self):
        feed_list = Feeds.query(Feeds.ui == self.ui.key).order(Feeds.title)
        self.response.set_cookie('active-tab', 'feeds')
        self.generate('feeds.html', {'feeds': feed_list})


class EditBM(BaseHandler):

    @util.login_required
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if self.ui.key == bm.ui:
            bm.url = self.request.get('url').encode('utf8')
            bm.title = self.request.get('title').encode('utf8')
            bm.comment = self.request.get('comment').encode('utf8')
            bm.put()
        self.redirect(self.request.referer)


class ArchiveBM(BaseHandler):

    @util.login_required
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if self.ui.key == bm.ui:
            if bm.trashed:
                bm.archived = False
                bm.trashed = False
            elif bm.archived:
                bm.archived = False
            else:
                bm.archived = True
            bm.put()


class TrashBM(BaseHandler):

    @util.login_required
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if self.ui.key == bm.ui:
            if bm.trashed is False:
                bm.archived = False
                bm.trashed = True
                bm.put()
            else:
                bm.key.delete()


class empty_trash(BaseHandler):

    @util.login_required
    def get(self):
        deferred.defer(util.delete_bms, self.ui.key)
        self.redirect(self.request.referer)


class StarBM(BaseHandler):

    @util.login_required
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if self.ui.key == bm.ui:
            if bm.starred is False:
                bm.archived = True
                bm.starred = True
                html = '<i class="icon-star"></i>'
            else:
                bm.starred = False
                html = '<i class="icon-star-empty"></i>'
            bm.put()
        self.response.write(html)


class ShareBM(BaseHandler):

    @util.login_required
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('id')))
        if self.ui.key == bm.ui:
            if bm.shared is False:
                bm.shared = True
                eye = '<i class="icon-eye-open"></i>'
            else:
                bm.shared = False
                eye = '<i class="icon-eye-close"></i>'
            bm.put()
        self.response.write(eye)


class cerca(BaseHandler):

    @util.login_required
    def post(self):
        query_string = self.request.get('query_string')
        try:
            results = search.Index(name=self.ui.key.id()).search(query_string)
            bms_ids = [int(doc.doc_id) for doc in results]
            keys = [ndb.Key(Bookmarks, id) for id in bms_ids]
            bms = ndb.get_multi(keys)
            html = self.generate('frame.html', {'bms': bms})
            self.response.write(html)
        except search.Error:
            pass


class AddFeed(BaseHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()
        self.redirect(self.request.referer)

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
                           last_id=d['items'][2].id).put()
            deferred.defer(util.pop_feed, feed_k)
        self.redirect('/feeds')


class GetComment(webapp2.RequestHandler):

    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.response.write(bm.comment)


class GetEdit(webapp2.RequestHandler):

    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.render('edit.html', {'bm': bm})


class CheckFeed(webapp2.RequestHandler):

    @util.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(util.pop_feed, feed.key)


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
    def get(self):
        old = Bookmarks.get_by_id(int(self.request.get('bm')))
        deferred.defer(util.submit_bm, feedk=None, uik=self.ui.key,
                       title=old.title, url=old.url, comment=old.comment)


class ReceiveMail(webapp2.RequestHandler):

    def post(self):
        from email import utils
        message = mail.InboundEmailMessage(self.request.body)
        texts = message.bodies('text/plain')
        for text in texts:
            txtmsg = ""
            txtmsg = text[1].decode().strip()
        email = utils.parseaddr(message.sender)[1]
        ui = UserInfo.query(UserInfo.email == email).get()
        util.submit_bm(feedk=None,
                       uik=ui.key,
                       url=txtmsg.encode('utf8'),
                       title=self.get_subject(txtmsg.encode('utf8'), message),
                       comment='Sent via email')

    def get_subject(self, o, message):
        from email import header
        try:
            return header.decode_header(message.subject)[0][0]
        except:
            return o

app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/admin', AdminPage),
    ('/logout', Logout),
    ('/search', cerca),
    (r'/bms/(.*)', Main_Frame),
    ('/submit', AddBM),
    ('/copy', CopyBM),
    ('/feed', AddFeed),
    ('/edit', EditBM),
    ('/checkfeed', CheckFeed),
    ('/archive', ArchiveBM),
    ('/trash', TrashBM),
    ('/empty_trash', empty_trash),
    ('/setting', SettingPage),
    ('/feeds', FeedsPage),
    ('/setmys', SetMys),
    ('/setdaily', SetDaily),
    ('/setnotify', SetNotify),
    ('/star', StarBM),
    ('/share', ShareBM),
    ('/save_email', SaveEmail),
    ('/getcomment', GetComment),
    ('/getedit', GetEdit),
    (r'/bm/(.*)', ItemPage),
    ('/upload', util.UploadDelicious),
    ('/_ah/mail/post@.*', ReceiveMail),
], debug=util.debug, config=util.config)

if __name__ == "__main__":
    app.run()
