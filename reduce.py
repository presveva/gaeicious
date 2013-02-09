#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.ext import ndb
from models import *
from mapreduce import operation as op


def remove_bm(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    bm = ndb_key.get()
    try:
        if bm.trashed == True:
            bm.key.delete()
            yield op.counters.Increment("eliminati")
        else:
            yield op.counters.Increment("rimasti")
    except:
        yield op.counters.Increment("errori")


def Attributi(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    bm = ndb_key.get()
    try:
        delattr(bm, 'analizzato')
        bm.put()
        yield op.counters.Increment("processati")
    except:
        yield op.counters.Increment("errori")


# class AttributiSvuotaIndex(webapp2.RequestHandler):
#     def get(self):
#         """Delete all the docs in the given index."""
#         doc_index = search.Index(name=self.request.get('index_name'))
#         while True:
#             document_ids = [document.doc_id for document in doc_index.list_documents(ids_only=True)]
#             if not document_ids:
#                     break
#             doc_index.remove(document_ids)
#         self.redirect(self.request.referer)

