#!/usr/bin/env python
# coding: utf-8

from daemon import settings, create_app
app = create_app(settings.settings)

if __name__ == "__main__":
    if app.debug:
        # for debugging purposes, we run Flask own server, and also it's
        # wonderful debugger. BTW: it automatically reloads
        app.run(host=app.config["debug_address"][0],
                port=app.config["debug_address"][1])
    else:
        # for production, we use Tornado super-duper fast HTTP server
        from tornado.httpserver import HTTPServer
        from tornado.wsgi import WSGIContainer
        from tornado.ioloop import IOLoop
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(app.config["address"][1], app.config["address"][0])
        IOLoop.instance().start()
