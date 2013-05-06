import util
import webapp2
import tweepy
import secret
from main import BaseHandler
from google.appengine.ext import ndb
from webapp2_extras import routes
from models import Followers

# callback_url = 'http://box.dinoia.eu/twitter/'
auth = tweepy.OAuthHandler(secret.consumer_token,
                           secret.consumer_secret)


class TwitterPage(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
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
        self.generate('twitter.html', {'tweets': tweets, 'ui': ui})


class Retweet(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
        auth.set_access_token(ui.access_k, ui.access_s)
        api = tweepy.API(auth)
        id_str = self.request.get('id_str')
        api.retweet(id_str)


class Tweet(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
        auth.set_access_token(ui.access_k, ui.access_s)
        api = tweepy.API(auth)
        text = self.request.get('text_tweet')
        api.update_status(text)
        self.redirect(self.request.referer)


class check(BaseHandler):

    @util.login_required
    def get(self):
        ui = self.ui
        ndb.delete_multi(ui.lost_foll())
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
    routes.RedirectRoute(
        '/twitter/', TwitterPage, name='Twitter', strict_slash=True),
    routes.PathPrefixRoute('/twitter', [
                           webapp2.Route('/check', check),
                           webapp2.Route('/retweet', Retweet),
                           webapp2.Route('/tweet', Tweet),
                           ]), ])

if __name__ == "__main__":
    app.run()
