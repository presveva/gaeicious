#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import util
import submit
import webapp2
from webapp2_extras import json
from google.appengine.api import users, app_identity, search
from google.appengine.ext import ndb, blobstore, deferred
from models import *


class BaseHandler(webapp2.RequestHandler):
    @property
    def ui(self):
        user = users.get_current_user()
        if user:
            return UserInfo.get_or_insert(str(user.user_id()), user=user)

    def render(self, _template, _values):
        template = util.jinja_environment.get_template(_template)
        return template.render(_values)

    def send_json(self, _values):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.encode(_values))

    def generate(self, template_name, template_values={}):
        if users.get_current_user():
            url = users.create_logout_url('/')
            urltext = 'Logout'
        else:
            url = users.create_login_url('/')
            urltext = 'Login'
        values = {
            'url': url, 'urltext': urltext, 'ui': self.ui,
            'brand': app_identity.get_application_id(),
            'admin': users.is_current_user_admin()
        }
        values.update(template_values)
        template = util.jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class HomePage(BaseHandler):
    def get(self):
        if users.get_current_user():
            self.generate('home.html', {})
        else:
            self.response.set_cookie('active-tab', 'hero')
            self.generate('hero.html', {})


class Main_Frame(BaseHandler):
    def get(self, page):
        if users.get_current_user():
            bmq = self.bmq(page)
            cursor = ndb.Cursor(urlsafe=self.request.get('cursor'))
            self.build(page, bmq, cursor)
        else:
            self.redirect('/')

    def bmq(self, page):
        q1 = Bookmarks.query(Bookmarks.user == users.get_current_user())
        q2 = q1.filter(Bookmarks.trashed == False).order(-Bookmarks.data)

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
                                  Bookmarks.shared == True).order(-Bookmarks.data)
        else:
            bmq = q2.filter(Bookmarks.archived == False)
        return bmq

    def build(self, page, bmq, cursor):
        bms, next_curs, more = bmq.fetch_page(15, start_cursor=cursor)
        next_c = next_curs.urlsafe() if more else None
        if page == 'stream':
            html = self.render('stream.html', {'bms': bms})
        else:
            html = self.render('frame.html', {'bms': bms})
        more = self.render('more.html', {'cursor': next_c})
        self.response.set_cookie('active-tab', page)
        self.send_json({"html": html, "more": more})


class ItemPage(BaseHandler):
    def get(self, id):
        bm = Bookmarks.get_by_id(int(id))
        if bm.shared == True:
            self.generate('item.html', {'bm': bm})
        else:
            self.redirect('/')


class SettingPage(BaseHandler):
    def get(self):
        ui = self.ui
        upload_url = blobstore.create_upload_url('/upload')
        brand = app_identity.get_application_id()
        bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+'&comment='+document.getSelection().toString()
""" % (self.request.host_url, ui.email)
        self.response.set_cookie('mys', '%s' % ui.mys)
        self.response.set_cookie('daily', '%s' % ui.daily)
        self.response.set_cookie('active-tab', 'setting')
        self.generate('setting.html', {'bookmarklet': bookmarklet,
                      'upload_url': upload_url, 'brand': brand, })


class FeedsPage(BaseHandler):
    def get(self):
        feed_list = Feeds.query(Feeds.user == users.get_current_user())
        feed_list = feed_list.order(-Feeds.data)
        self.response.set_cookie('active-tab', 'feeds')
        self.generate('feeds.html', {'feeds': feed_list})


class EditBM(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            bm.url = self.request.get('url').encode('utf8')
            bm.title = self.request.get('title').encode('utf8')
            bm.comment = self.request.get('comment').encode('utf8')
            bm.put()
        self.redirect(self.request.referer)


class ArchiveBM(BaseHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            if bm.trashed:
                bm.archived = False
                bm.trashed = False
                bm.feed = None
            elif bm.archived:
                bm.archived = False
            else:
                bm.archived = True
                bm.feed = None
            bm.put()


class TrashBM(BaseHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            if bm.trashed == False:
                bm.archived = False
                bm.trashed = True
                bm.put()
            else:
                bm.key.delete()


class StarBM(webapp2.RequestHandler):
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


class ShareBM(webapp2.RequestHandler):
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


class cerca(BaseHandler):
    def post(self):
        user = users.get_current_user()
        query_string = self.request.get('query_string')
        try:
            results = search.Index(name='%s' % user.user_id()).search(query_string)
            bms_ids = [int(doc.doc_id) for doc in results]
            keys = [ndb.Key(Bookmarks, id) for id in bms_ids]
            bms = ndb.get_multi(keys)
            html = self.generate('frame.html', {'bms': bms})
            self.response.write(html)
        except search.Error:
            pass


class GetComment(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.response.write(bm.comment)


class GetEdit(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.render('edit.html', {'bm': bm})


class CheckFeed(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(submit.pop_feed, feed.key)

###################################################
## Setting page
###################################################


class SetMys(webapp2.RequestHandler):
    def get(self):
        ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
        if ui.mys == False:
            ui.mys = True
            html = '<i class="icon-thumbs-up"></i> <b>Enabled </b>'
        else:
            ui.mys = False
            html = '<i class="icon-thumbs-down"></i> <b>Disabled</b>'
        ui.put()
        self.response.write(html)


class SetDaily(webapp2.RequestHandler):
    def get(self):
        ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
        if ui.daily == False:
            ui.daily = True
            html = '<i class="icon-thumbs-up"></i> <b>Enabled </b>'
        else:
            ui.daily = False
            html = '<i class="icon-thumbs-down"></i> <b>Disabled</b>'
        ui.put()
        self.response.write(html)


class SetNotify(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        feed.notify = self.request.get('notify')
        feed.put()


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/search', cerca),
    (r'/bms/(.*)', Main_Frame),
    ('/submit', submit.AddBM),
    ('/copy', submit.CopyBM),
    ('/upload', submit.UploadDelicious),
    ('/feed', submit.AddFeed),
    ('/edit', EditBM),
    ('/checkfeed', CheckFeed),
    ('/archive', ArchiveBM),
    ('/trash', TrashBM),
    ('/setting', SettingPage),
    ('/feeds', FeedsPage),
    ('/setmys', SetMys),
    ('/setdaily', SetDaily),
    ('/setnotify', SetNotify),
    ('/star', StarBM),
    ('/share', ShareBM),
    ('/getcomment', GetComment),
    ('/getedit', GetEdit),
    (r'/bm/(.*)', ItemPage),
], debug=util.debug, config=util.config)

if __name__ == "__main__":
    app.run()
