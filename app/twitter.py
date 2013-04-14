# import util
import webapp2
import tweepy
import secret
from main import BaseHandler
from google.appengine.ext import ndb
from webapp2_extras import routes

# callback_url = 'http://dev.box.dinoia.eu/twitter/'
auth = tweepy.OAuthHandler(secret.consumer_token,
                           secret.consumer_secret)


class Twittero(ndb.Model):
    screen_name = ndb.StringProperty()
    email = ndb.StringProperty()
    access_k = ndb.StringProperty()
    access_s = ndb.StringProperty()
    last_id = ndb.StringProperty()
    data = ndb.DateTimeProperty(auto_now=True)

    def followers_ids(self):
        followers = Followers.query(Followers.ui == self.key).fetch()
        return [follower.user_id for follower in followers]

    def new_foll(self):
        return Followers.query(Followers.ui == self.key,
                               Followers.new == True)

    def lost_foll(self):
        return Followers.query(Followers.ui == self.key,
                               Followers.lost == True)


class Followers(ndb.Model):
    ui = ndb.KeyProperty(kind=Twittero)
    user_id = ndb.IntegerProperty()
    screen_name = ndb.StringProperty()
    data = ndb.DateTimeProperty(auto_now=True)
    new = ndb.BooleanProperty(default=False)
    lost = ndb.BooleanProperty(default=False)


class TwitterPage(BaseHandler):
    def get(self):
        oauth_verifier = self.request.get("oauth_verifier")
        screen_name = self.request.cookies.get('screen_name')
        if oauth_verifier:
            auth.get_access_token(oauth_verifier)
            api = tweepy.API(auth)
            screen_name = api.me().screen_name
            old_ui = Twittero.query(Twittero.screen_name == screen_name)
            if old_ui.get():
                ui = old_ui.get()
            else:
                ui = Twittero()
            ui.screen_name = screen_name
            ui.access_k = auth.access_token.key
            ui.access_s = auth.access_token.secret
            ui.put()
            self.response.set_cookie('screen_name', screen_name)
            self.redirect('/twitter/')
        elif screen_name is not None:
            ui = Twittero.query(Twittero.screen_name == screen_name).get()
            auth.set_access_token(ui.access_k, ui.access_s)
            api = tweepy.API(auth)
            new_tweets = api.home_timeline()
            ntw_ids = [tw.id_str for tw in new_tweets]
            tw_ids = []
            n = 0
            while ntw_ids[n] != ui.last_id and n < (len(ntw_ids) - 1):
                tw_ids.append(ntw_ids[n])
                n += 1
            tweets = [api.get_status(tw_id) for tw_id in tw_ids]
            ui.last_id = new_tweets[0].id_str
            ui.put()
            # template = util.jinja_environment.get_template('twitter.html')
            # self.response.write(template.render({'tweets': tweets, 'ui': ui}))
            self.generate('twitter.html', {'tweets': tweets, 'ui': ui})
        else:
            redirect_url = auth.get_authorization_url()
            # template = util.jinja_environment.get_template('twitter.html')
            # self.response.write(template.render({'redirect_url': redirect_url}))
            self.generate('twitter.html', {'redirect_url': redirect_url})


class Retweet(webapp2.RequestHandler):
    def get(self):
        screen_name = self.request.cookies.get('screen_name')
        ui = Twittero.query(Twittero.screen_name == screen_name).get()
        auth.set_access_token(ui.access_k, ui.access_s)
        api = tweepy.API(auth)
        id_str = self.request.get('id_str')
        api.retweet(id_str)


class Tweet(webapp2.RequestHandler):
    def get(self):
        screen_name = self.request.cookies.get('screen_name')
        ui = Twittero.query(Twittero.screen_name == screen_name).get()
        auth.set_access_token(ui.access_k, ui.access_s)
        api = tweepy.API(auth)
        text = self.request.get('text_tweet')
        api.update_status(text)
        self.redirect(self.request.referer)


class check(webapp2.RequestHandler):
    def get(self):
        screen_name = self.request.cookies.get('screen_name')
        ui = Twittero.query(Twittero.screen_name == screen_name).get()
        ndb.delete_multi([f.key for f in ui.lost_foll()])
        auth.set_access_token(ui.access_k, ui.access_s)
        api = tweepy.API(auth)
        old_list = ui.followers_ids()
        new_list = api.followers_ids()
        put_queue = []
        new_foll = [nf for nf in new_list if nf not in old_list]
        for nf in new_foll:
            f = Followers(ui=ui.key,
                          user_id=nf,
                          screen_name=api.get_user(nf).screen_name,
                          new=True)
            put_queue.append(f)
        for lf in old_list:
            if lf not in new_list:
                exfollower = Followers.query(Followers.user_id == lf).get()
                exfollower.lost = True
                put_queue.append(exfollower)
        for sf in old_list:
            if sf in new_list:
                follower = Followers.query(Followers.user_id == sf).get()
                if follower.new is True:
                    follower.new = False
                    put_queue.append(follower)
        ndb.put_multi(put_queue)
        self.redirect('/twitter/')

app = webapp2.WSGIApplication([
    routes.RedirectRoute('/twitter/', TwitterPage, name='Twitter', strict_slash=True),
    routes.PathPrefixRoute('/twitter', [
                           webapp2.Route('/check', check),
                           webapp2.Route('/retweet', Retweet),
                           webapp2.Route('/tweet', Tweet),
                           ]), ])

if __name__ == "__main__":
    app.run()
