#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.ext import ndb
from models import *
from mapreduce import operation as op


def delattr(db_key):
    ndb_key = ndb.Key.from_old_key(db_key)
    ent = ndb_key.get()
    yield op.counters.Increment("entità lette")
    try:
        delattr(ent, u'user_id')
        ent.put()
        yield op.counters.Increment("proprietà rimosse")
    except:
        pass
