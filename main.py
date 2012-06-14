# coding: utf-8

import tornado.ioloop
import tornado.web
import os
import simplejson as json
import rrdtool


def filter_dirs(name):
    for i in ["memory", "cpu", "interface", "disk", "net"]:
        if name.startswith(i):
            return True
    return False


class ListHosts(tornado.web.RequestHandler):
    def get(self):
        try:
            data_dir = self.application.settings["collectd_directory"]
            data_dir = os.path.join(data_dir, "rrd")
            self.write(json.dumps(
                [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
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


class GetData(tornado.web.RequestHandler):
    def get(self, host, metrics, rrd, start=None, end=None):
        if not filter_dirs(metrics):
            # TODO: we probably don't want to have this
            raise tornado.web.HTTPError(404, "Illegal collectd metrics directory `%s`" % metrics)

        rrd = rrd.split("|")

        return_data = dict()

        try:
            data_dir = self.application.settings["collectd_directory"]
            data_dir = os.path.join(data_dir, "rrd")
            host_dir = os.path.join(data_dir, host)
            metrics_dir = os.path.join(host_dir, metrics)

            for i in rrd:
                rrd_file = os.path.join(metrics_dir, i)

                # TODO: handle rrd errors better?
                if not start:
                    #start = str(rrdtool.first(str(rrd_file)))
                    start = "-1d"
                if not end:
                    #end = str(rrdtool.last(str(rrd_file)))
                    end = "now"

                data = rrdtool.fetch(str(rrd_file), "AVERAGE", "-s", start, "-e", end)
                D = []
                for k, v in enumerate(data[2]):
                    # time is being multiplied by 1000, because JS handles EPOCH
                    # as miliseconds, not seconds since 1/1/1970 00:00:00
                    D.append([(data[0][0] + data[0][2] * k) * 1000, v[0]])

                return_data[i] = {"label": i, "data": D}
            self.write(json.dumps(return_data))

        except OSError:
            raise tornado.web.HTTPError(404, "Collectd metrics `%s` not found" % (rrd_file, ))

        except rrdtool.error, e:
            raise tornado.web.HTTPError(500, "RRDTool is borked: `%s`" % str(e))


class Threshold(tornado.web.RequestHandler):
    """
    Set and get current thresholds for given RRD
    """
    pass


application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler, {"url": "/page/index.html"}),
    (r"/page/(.*)", tornado.web.StaticFileHandler, {"path": "./page"}),
    (r"/list_hosts", ListHosts),
    (r"/host/(.*)/list_metrics", ListMetrics),
    (r"/host/(.*)/list_rrds/(.*)", ListRRDs),
    (r"/get/(.*)/(.*)/(.*)/?(\d*)/?(\d*)/?", GetData),
    (r"/threshold/(.*)/(.*)/(.*)", Threshold),  # should support GET & POST
    # it's likely that any other URL will be used for configuration protocol
],
collectd_directory="/var/lib/collectd/",
debug=True)


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
