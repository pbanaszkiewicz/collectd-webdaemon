# coding: utf-8

import os
from xml.dom.minidom import parseString as parse_XML

import simplejson as json
import rrdtool

from flask import Flask, request, redirect

from settings import settings
from utils import filter_dirs, collectd_to_XML, XML_to_collectd


app = Flask(__name__)
app.config.update(settings)


@app.route("/")
def index():
    return redirect("/static/index.html")


@app.route("/list_hosts")
def list_hosts():
    """
    Return JSONified list of all hosts whose data is being collected by collectd.
    """
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
    """
    Return JSONified list of directories (which contain RRD files) of particular
    host.
    """
    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        return json.dumps(
            # TODO: filter_dirs probably should be cut off
            sorted([d for d in os.listdir(host_dir) if filter_dirs(d) and os.path.isdir(os.path.join(host_dir, d))])
        )
    except OSError:
        return ("Collectd hostname directory `%s` was not found" % host_dir, 404)


@app.route("/host/<host>/list_rrds/<metrics>")
def list_rrds(host, metrics):
    """
    Return JSONified list of RRD files in particular directory.
    """
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


@app.route("/get/<host>/<metrics>/<rrd>/", defaults={"start": None, "end": None})
@app.route("/get/<host>/<metrics>/<rrd>/<start>/", defaults={"end": None})
@app.route("/get/<host>/<metrics>/<rrd>/<start>/<end>")
def get_data(host, metrics, rrd, start=None, end=None):
    """
    Return JSON dictionary of pairs RRD file name and it's parsed content.

    Actually supports only first value, even though RRD file can store more at
    one frame.

    Supports many RRD files from one directory (file names must be separated
    by "|" [pipe] sign.)
    """
    # TODO: we probably don't want to have this
    #if not filter_dirs(metrics):
    #    return ("Illegal collectd metrics directory `%s`" % metrics, 404)

    rrd = rrd.split("|")

    return_data = dict()

    try:
        data_dir = app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        metrics_dir = os.path.join(host_dir, metrics)

        for i in rrd:
            rrd_file = os.path.join(metrics_dir, i)

            if not start:
                start = "-1h"
            if not end:
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


@app.route("/threshold/", methods=["GET", "POST"])
def threshold():
    """
    Set and get current thresholds for collectd daemon.

    GET method:  obtain configuration
    POST method: set configuration
    """
    path = app.config["collectd_threshold_file"]

    if request.method == "GET":
        try:
            return collectd_to_XML(open(path, "r").read())
        except IOError:
            # not found OR no permission
            return ("File not found", 404)

    elif request.method == "POST":
        XML = request.form['configuration']

        # checking XML for good structure
        # an exception will result in HTTP 500
        parse_XML(XML)

        F = open(path, "w")
        F.write(XML_to_collectd(XML))
        F.close()

        # TODO: run collectd to test if the configuration is fine
        #       copy of previous configuration will be needed in case of failure

        return ("File saved.", 200)


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
        http_server.listen()
        IOLoop.instance().start()
