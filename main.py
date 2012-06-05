# coding: utf-8

import tornado.ioloop
import tornado.web
import os
import simplejson as json


def filter_dirs(name):
    for i in ["memory", "cpu", "interface", "disk"]:
        if name.startswith(i):
            return True
    return False


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class TimeHandler(tornado.web.RequestHandler):
    """
    This handler simply prints out current EPOCH time (ie. seconds since
    01/01/1970 00:00:00)
    Why? Well, RRD files have time specified, but it's in EPOCH format. Thus
    the browser must calculate the delta between user's system time and the time
    printed out by this Handler. This delta will then be used to show those
    nice looking graphs with accurate time on time-axis.
    """
    def get(self):
        import time
        self.write(str(int(time.time())))


class ListHosts(tornado.web.RequestHandler):
    def get(self):
        try:
            data_dir = self.application.settings["collectd_directory"]
            data_dir = os.path.join(data_dir, "rrd")
            self.write(json.dumps(
                [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))] + ["dupa"]
            ))
        except OSError:
            raise tornado.web.HTTPError(404, "Collectd directory `%s` was not found" % data_dir)


class ListMetrics(tornado.web.RequestHandler):
    def get(self, host):
        try:
            data_dir = self.application.settings["collectd_directory"]
            data_dir = os.path.join(data_dir, "rrd")
            host_dir = os.path.join(data_dir, host)
            #self.write(json.dumps(os.listdir(host_dir)))
            self.write(json.dumps(
                sorted([d for d in os.listdir(host_dir) if filter_dirs(d) and os.path.isdir(os.path.join(host_dir, d))])
            ))
        except OSError:
            raise tornado.web.HTTPError(404, "Collectd hostname directory `%s` was not found" % host_dir)


class ListRRDs(tornado.web.RequestHandler):
    def get(self, host, metrics):
        try:
            data_dir = self.application.settings["collectd_directory"]
            data_dir = os.path.join(data_dir, "rrd")
            host_dir = os.path.join(data_dir, host)
            metrics_dir = os.path.join(host_dir, metrics)
            #self.write(json.dumps(os.listdir(host_dir)))
            self.write(json.dumps(
                sorted([d for d in os.listdir(metrics_dir) if d.endswith(".rrd")])
            ))
        except OSError:
            raise tornado.web.HTTPError(404, "Collectd metrics `%s@%s` were not found" % (metrics, host))


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/time", TimeHandler),
    (r"/list_hosts", ListHosts),
    (r"/page/(.*)", tornado.web.StaticFileHandler, {"path": "./page"}),
    (r"/host/(.*)/list_metrics", ListMetrics),
    (r"/host/(.*)/list_rrds/(.*)", ListRRDs),
],
collectd_directory="/var/lib/collectd/",
debug=True)


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
