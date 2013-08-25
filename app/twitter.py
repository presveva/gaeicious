#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from main import BaseHandler
from util import api, login_required, get_api
from webapp2 import WSGIApplication, Route, RequestHandler


class TwitterPage(BaseHandler):

    @login_required
    def get(self):
        new_api = get_api(self.ui.key)
        new_tweets = new_api.home_timeline()
        self.generate('twitter.html', {'tweets': new_tweets})


class Retweet(RequestHandler):

    @login_required
    def get(self):
        id_str = self.request.get('id_str')
        api.retweet(id_str)


class Tweet(RequestHandler):

    @login_required
    def get(self):
        text = self.request.get('text_tweet')
        api.update_status(text)
        self.redirect(self.request.referer)


class GetDetails(BaseHandler):

    @login_required
    def get(self):
        new_api = get_api(self.ui.key)
        from google.appengine.ext.ndb import Key
        bmk = Key(urlsafe=str(self.request.get('us')))
        tweet = new_api.get_status(int(bmk.id()))
        data = {
            "retweets": tweet.retweet_count,
            "favorites": tweet.favorite_count,
            "favico": tweet.user.profile_image_url,
            # "pic": tweet.entities['media'][0].media_url
        }
        self.send_json(data)


from webapp2_extras.routes import RedirectRoute, PathPrefixRoute
app = WSGIApplication([
    RedirectRoute('/twitter/', TwitterPage, name='Twitter', strict_slash=True),
    PathPrefixRoute('/twitter', [
                    Route('/details', GetDetails),
                    Route('/retweet', Retweet),
                    Route('/tweet', Tweet),
                    ]), ])

if __name__ == "__main__":
    app.run()
