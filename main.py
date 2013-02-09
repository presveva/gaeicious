#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import webapp2
import json
import logging
import util
import submit
from google.appengine.api import users, app_identity, search
from google.appengine.ext import ndb, blobstore, deferred
from models import *


class BaseHandler(webapp2.RequestHandler):
    @property
    def ui(self):
        if users.get_current_user():
            q = UserInfo.query(UserInfo.user == users.get_current_user())
            if q.get():
                return q.get()
            else:
                ui = UserInfo()
                ui.user = users.get_current_user()
                ui.put()
                return ui

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
            cursor = self.request.get('cursor')
            bmq = self.bmq(page)
            self.build(page, bmq, cursor)
        else:
            self.redirect('/')

    def bmq(self, page):
        q1 = Bookmarks.query(Bookmarks.user == users.get_current_user())
        q2 = q1.order(-Bookmarks.data)
        q3 = q2.filter(Bookmarks.trashed == False)

        if page == 'archived':
            bmq = q3.filter(Bookmarks.archived == True)
        elif page == 'shared':
            bmq = q3.filter(Bookmarks.shared == True)
        elif page == 'starred':
            bmq = q3.filter(Bookmarks.starred == True)
        elif page == 'trashed':
            bmq = q2.filter(Bookmarks.trashed == True)
        elif page == 'domain':
            bmq = q2.filter(Bookmarks.domain == self.request.get('domain'))
        elif page == 'stream':
            bmq = Bookmarks.query(Bookmarks.trashed == False,
                                  Bookmarks.shared == True)
            bmq = bmq.order(-Bookmarks.data)
        else:
            bmq = q3.filter(Bookmarks.archived == False)
        return bmq

    def build(self, page, bmq, cursor):
        c = ndb.Cursor(urlsafe=cursor)
        bms, next_curs, more = bmq.fetch_page(15, start_cursor=c)
        if more and next_curs:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        values = {'bms': bms, 'c': next_c, 'ui': self.ui}
        self.response.set_cookie('active-tab', page)  # todo
        if page == 'stream':
            tmpl = util.jinja_environment.get_template('stream.html')
        else:
            tmpl = util.jinja_environment.get_template('frame.html')
        self.response.headers['Content-Type'] = 'application/json'
        html = tmpl.render(values)
        tmpl1 = util.jinja_environment.get_template('more.html')
        more = tmpl1.render(values)
        data = json.dumps({"html": html, "more": more})
        self.response.write(data)


class StreamPage(BaseHandler):
    def get(self):
        if users.get_current_user():
            cursor = self.request.get('cursor')
            bmq = Bookmarks.query(Bookmarks.trashed == False,
                                  Bookmarks.shared == True)
            bmq = bmq.order(-Bookmarks.data)
            c = ndb.Cursor(urlsafe=cursor)
            bms, next_curs, more = bmq.fetch_page(15, start_cursor=c)
            if more and next_curs:
                next_c = next_curs.urlsafe()
            else:
                next_c = None
            values = {'bms': bms, 'c': next_c, 'ui': self.ui}
            self.generate('item.html', values)


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
            def txn():
                bm.url = self.request.get('url').encode('utf8')
                bm.title = self.request.get('title').encode('utf8')
                bm.comment = self.request.get('comment').encode('utf8')
                bm.put()
            ndb.transaction(txn)
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


class indicizza(webapp2.RequestHandler):
    def get(self):
        for ui in UserInfo.query():
            deferred.defer(util.index_bms,
                           ui,
                           _target='worker',
                           _queue='admin')
            self.redirect('/')


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
            logging.exception('Search failed')


class GetComment(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        self.response.write(bm.comment)


class GetEdit(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        template = util.jinja_environment.get_template('edit.html')
        values = {'bm': bm}
        html_page = template.render(values)
        self.response.write(html_page)


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


class CheckFeed(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(submit.pop_feed, feed.key, _target="worker", _queue="admin")

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


def main():
    app.run()

if __name__ == "__main__":
    main()
