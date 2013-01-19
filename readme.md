How to install
---
- checkout the [repository](https://github.com/presveva/gae.icio.us/zipball/master)
- create a new app in [appengine](https://appengine.google.com/)
- change the 'app-id' in app.yaml
- [deploy](https://developers.google.com/appengine/docs/python/tools/uploadinganapp#Uploading_the_App) in google app engine

Goodies
---
- Searchable
- Content optimization
    - Images, Youtube and Vimeo video is incorporated as comment
    - Urls is sanitized
    - Mail yourself (You can receive an email for each bookmark)
- Shared
    - All shared items are joined in a "stream page" open to members.

How to post
---
- Bookmarklet
  - Drag and drop the bookmarklet in your bookmarks bar
  - Selected text and click on bookmarklet
  - if you select a text, this is "insert as comment"
- Post via email
  - From: the email used in app-id
  - To: post@app-id.appspotmail.com
  - Subject: the title of the post
  - Body: only the link of the post
- Feed subscription
  - Add your feed urls in Feeds page
  - the app creates a new bookmark for each new item in the feed
  - if MYS is active you will get new posts in your inbox
- Import from Delicious
  - In setting page users can upload the delicious file.


Open source libraries used in gaeicious
---
- Twitter Bootstrap [github](https://github.com/twitter/bootstrap)
- jquery [github](https://github.com/jquery/jquery)
- jquery cookie [github](https://github.com/carhartl/jquery-cookie)
- Universal feed parser: [docs](http://packages.python.org/feedparser)


Copyright and license
---
Copyright 2013  [@presveva](https://github.com/presveva)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this work except in compliance with the License.
You may obtain a copy of the License in the LICENSE file, or at:

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.