#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.ext import ndb
from google.appengine.api import search, users
from models import *
from mapreduce import operation as op


def remove_bm(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    bm = ndb_key.get()
    try:
        if bm.user == users.User("bla@gmail.com"):
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


def reset_index(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    ui = ndb_key.get()
    """Delete all the docs in the given index."""
    doc_index = search.Index(name=ui.user.user_id())

    while True:
        # Get a list of documents populating only the doc_id field and extract the ids.
        document_ids = [document.doc_id
                        for document in doc_index.get_range(ids_only=True)]
        if not document_ids:
            break
        # Remove the documents for the given ids from the Index.
        doc_index.delete(document_ids)
    # doc_index.deleteSchema()


def reindex_all(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    bm = ndb_key.get()
    index = search.Index(name=bm.user.user_id())
    doc = search.Document(doc_id=str(bm.id),
                          fields=[
                          search.TextField(name='url', value=bm.url),
                          search.TextField(name='title', value=bm.title),
                          search.HtmlField(name='comment', value=bm.comment)
                          ])
    try:
        index.put(doc)
    except search.Error:
        logging.exception('Add failed')
