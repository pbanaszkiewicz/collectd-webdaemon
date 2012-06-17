# coding: utf-8

import os
import simplejson as json
from flask import Flask, redirect
import rrdtool


def filter_dirs(name):
    for i in ["memory", "cpu", "interface", "disk", "net"]:
        if name.startswith(i):
            return True
    return False


app = Flask(__name__)
app.config.update(
    collectd_directory="/var/lib/collectd/",
    DEBUG=True,
)


@app.route("/")
def index():
    return redirect("/static/index.html")


@app.route("/list_hosts")
def list_hosts():
    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        return json.dumps(
            [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        )
    except OSError:
        return ("Collectd directory `%s` was not found" % data_dir, 404)


@app.route("/host/<host>/list_metrics")
def list_metrics(host):
    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        return json.dumps(
            sorted([d for d in os.listdir(host_dir) if filter_dirs(d) and os.path.isdir(os.path.join(host_dir, d))])
        )
    except OSError:
        return ("Collectd hostname directory `%s` was not found" % host_dir, 404)


@app.route("/host/<host>/list_rrds/<metrics>")
def list_rrds(host, metrics):
    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        metrics_dir = os.path.join(host_dir, metrics)
        return json.dumps(
            sorted([d for d in os.listdir(metrics_dir) if d.endswith(".rrd")])
        )
    except OSError:
        return ("Collectd metrics `%s@%s` were not found" % (metrics, host), 404)


@app.route("/get/<host>/<metrics>/<rrd>/<start>/<end>")
def get_data(host, metrics, rrd, start=None, end=None):
    if not filter_dirs(metrics):
        # TODO: we probably don't want to have this
        return ("Illegal collectd metrics directory `%s`" % metrics, 404)

    rrd = rrd.split("|")

    return_data = dict()

    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        metrics_dir = os.path.join(host_dir, metrics)

        for i in rrd:
            rrd_file = os.path.join(metrics_dir, i)

            # TODO: handle rrd errors better?
            if not start:
                #start = str(rrdtool.first(str(rrd_file)))
                start = "-1h"
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
        return json.dumps(return_data)

    except OSError:
        return ("Collectd metrics `%s` not found" % (rrd_file, ), 404)

    except rrdtool.error, e:
        return ("RRDTool is borked: `%s`" % str(e), 500)


@app.route("/threshold/")
def threshold():
    """
    Set and get current thresholds for given RRD
    """
    return ""


#application = tornado.web.Application([
#    (r"/page/(.*)", tornado.web.StaticFileHandler, {"path": "./page"}),
#    # it's likely that any other URL will be used for configuration protocol
#],
#collectd_directory="/var/lib/collectd/",
#debug=True)


if __name__ == "__main__":
    from tornado.httpserver import HTTPServer
    from tornado.wsgi import WSGIContainer
    from tornado.ioloop import IOLoop
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8888)
    IOLoop.instance().start()
