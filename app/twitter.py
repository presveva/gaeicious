import webapp2
import tweepy
from . import secret, util
from .main import BaseHandler
from webapp2_extras import routes

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
        while n < (len(ntw_ids) - 1):
        # while ntw_ids[n] != ui.last_id and n < (len(ntw_ids) - 1):
            tw_ids.append(ntw_ids[n])
            n += 1
        tweets = [api.get_status(tw_id) for tw_id in tw_ids]
        # ui.last_id = new_tweets[0].id_str
        # ui.put()
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


app = webapp2.WSGIApplication([
    routes.RedirectRoute(
        '/twitter/', TwitterPage, name='Twitter', strict_slash=True),
    routes.PathPrefixRoute('/twitter', [
                           webapp2.Route('/retweet', Retweet),
                           webapp2.Route('/tweet', Tweet),
                           ]), ])

if __name__ == "__main__":
    app.run()
