#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
import webapp2
import os
from google.appengine.api import users, app_identity
from google.appengine.ext import ndb, blobstore
from handlers import ajax, util, core, submit
from handlers.models import Bookmarks, UserInfo, Feeds, Tags


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates', 'partials']))
jinja_environment.filters['dtf'] = util.dtf


class BaseHandler(webapp2.RequestHandler):

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
            url = users.create_logout_url("/")
            linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            linktext = 'Login'
        values = {
            'brand': app_identity.get_application_id(),
            'url': url,
            'linktext': linktext,
            'ui': self.ui(),
            'admin': users.is_current_user_admin()
            }
        values.update(template_values)
        template = jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class Main_Frame(BaseHandler):
    def get(self):
        if users.get_current_user():
            page = self.request.get('page')
            cursor = self.request.get('cursor')
            arg1 = self.request.get('arg1')
            arg2 = self.request.get('arg2')
            bmq = self.bmq(page, arg1, arg2)
            self.build(page, bmq, cursor, arg1, arg2)
        else:
            self.response.set_cookie('active-tab', 'hero')
            self.generate('hero.html', {})

    def bmq(self, page, arg1, arg2):
        q1 = Bookmarks.query(Bookmarks.user == users.get_current_user())
        q2 = q1.order(-Bookmarks.data)
        q3 = q2.filter(Bookmarks.trashed == False)
        t1 = Tags.query(Tags.user == users.get_current_user())

        if page == 'archived':
            bmq = q3.filter(Bookmarks.archived == True)
        elif page == 'shared':
            bmq = q3.filter(Bookmarks.shared == True)
        elif page == 'starred':
            bmq = q3.filter(Bookmarks.starred == True)
        elif page == 'untagged':
            bmq = q3.filter(Bookmarks.have_tags == False)
        elif page == 'trashed':
            bmq = q2.filter(Bookmarks.trashed == True)
        elif page == 'domain':
            bmq = q2.filter(Bookmarks.domain == arg1)
        elif page == 'filter':
            tag1 = t1.filter(Tags.name == arg1).get()
            bmq = q2.filter(Bookmarks.tags == tag1.key)
        elif page == 'refine':
            tag1 = t1.filter(Tags.name == arg1).get()
            tag2 = t1.filter(Tags.name == arg2).get()
            bmq = q2.filter(Bookmarks.tags == tag1.key)
            bmq = bmq.filter(Bookmarks.tags == tag2.key)
        elif page == 'stream':
            bmq = Bookmarks.query(Bookmarks.trashed == False)
            bmq = bmq.filter(Bookmarks.shared == True)
            bmq = bmq.order(-Bookmarks.data)
        else:
            bmq = q3.filter(Bookmarks.archived == False)
        return bmq

    def build(self, page, bmq, cursor, arg1, arg2):
        c = ndb.Cursor(urlsafe=cursor)
        bms, next_curs, more = bmq.fetch_page(15, start_cursor=c)
        if more and next_curs:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        values = {'bms': bms,
                  'c': next_c,
                  'ui': self.ui(),
                  'arg1': arg1,
                  'arg2': arg2,
                  'bm_ids': list(bm.id for bm in bms)
                  }
        if page == '':
            self.response.set_cookie('active-tab', 'inbox')
            self.generate('home.html', values)
        else:
            if page == 'stream':
                temp = jinja_environment.get_template('stream.html')
            else:
                temp = jinja_environment.get_template('frame.html')
            # if page == 'inbox':
                # values['bm_ids'] = list(bm.id for bm in bms)
            html = temp.render(values)
            self.response.set_cookie('active-tab', page)
            self.response.write(html)


class OtherPage(BaseHandler):
    def get(self):
        if users.get_current_user():
            page = self.request.get('page')
            if page == 'setting':
                self.setting()
            elif page == 'feeds':
                self.feeds()
            elif page == 'admin':
                self.admin()
            else:
                self.redirect('/')

    def setting(self):
        ui = self.ui()
        upload_url = blobstore.create_upload_url('/upload')
        brand = app_identity.get_application_id()
        bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, ui.email)

        temp = jinja_environment.get_template('setting.html')
        html = temp.render({'bookmarklet': bookmarklet,
                           'upload_url': upload_url,
                           'brand': brand,
                           })
        self.response.set_cookie('mys', '%s' % ui.mys)
        self.response.set_cookie('daily', '%s' % ui.daily)
        self.response.set_cookie('twitt', '%s' % ui.twitt)
        self.response.set_cookie('active-tab', 'setting')
        self.response.write(html)

    def feeds(self):
        feed_list = Feeds.query(Feeds.user == users.get_current_user())
        feed_list = feed_list.order(-Feeds.data)
        temp = jinja_environment.get_template('feeds.html')
        html = temp.render({'feeds': feed_list})
        self.response.set_cookie('active-tab', 'feeds')
        self.response.write(html)

    def admin(self):
        if users.is_current_user_admin():
            ui = self.ui()
            self.response.set_cookie('active-tab', 'admin')
            temp = jinja_environment.get_template('admin.html')
            html = temp.render({'ui': ui})
            self.response.write(html)
        else:
            self.redirect('/')


debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
app = webapp2.WSGIApplication([
    ('/', Main_Frame),
    ('/other', OtherPage),
    ('/submit', submit.AddBM),
    ('/_ah/mail/post@.*', submit.ReceiveMail),
    ('/copy', submit.CopyBM),
    ('/upload', submit.UploadDelicious),
    ('/feed', submit.AddFeed),
    ('/edit', core.EditBM),
    # ('/deltag', core.DeleteTag),
    ('/atf', core.AssTagFeed),
    ('/rtf', core.RemoveTagFeed),
    ('/empty_trash', core.Empty_Trash),
    ('/checkfeed', core.CheckFeed),
    ('/admin/upgrade', core.Upgrade),
    ('/admin/script', core.Script),
    ('/admin/digest', core.SendDigest),
    ('/admin/activity', core.SendActivity),
    ('/admin/check', core.CheckFeeds),
    ('/admin/delattr', core.del_attr),
    ('/get_tips', ajax.get_tips),
    ('/get_refine_tags', ajax.get_refine_tags),
    ('/get_empty_trash', ajax.get_empty_trash),
    ('/gettagcloud', ajax.gettagcloud),
    ('/setmys', ajax.SetMys),
    ('/setdaily', ajax.SetDaily),
    ('/setnotify', ajax.SetNotify),
    ('/settwitt', ajax.SetTwitt),
    ('/archive', ajax.ArchiveBM),
    ('/trash', ajax.TrashBM),
    ('/star', ajax.StarBM),
    ('/share', ajax.ShareBM),
    ('/addtag', ajax.AddTag),
    ('/removetag', ajax.RemoveTag),
    ('/assigntag', ajax.AssignTag),
    ('/gettags', ajax.GetTags),
    ('/gettagsfeed', ajax.GetTagsFeed),
    ('/getcomment', ajax.GetComment),
    ('/getedit', ajax.GetEdit),
    ('/archive_all', core.archive_all),
    ('/trash_all', core.trash_all),
    ], debug=debug)


def main():
    app.run()

if __name__ == "__main__":
    main()
