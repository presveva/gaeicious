# appstats_MAX_STACK = 30
appstats_SHELL_OK = True
# appstats_MAX_LOCALS = 0
# appstats_DUMP_LEVEL = 3
# appstats_FILTER_LIST = [{'PATH_INFO': '<path[12]>*'}]


def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)
    return app

remoteapi_CUSTOM_ENVIRONMENT_AUTHENTICATION = ('HTTP_X_APPENGINE_INBOUND_APPID', ['gaeicious'])
