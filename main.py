#!/usr/bin/env python
# coding: utf-8

import os
#from xml.dom.minidom import parseString as parse_XML
import re
from collections import OrderedDict

import sqlite3
import simplejson as json
import rrdtool

from flask import Flask, g, request, redirect, make_response, url_for
from flask.views import MethodView

from settings import settings
from utils import filter_dirs


app = Flask(__name__)
app.config.update(settings)


def connect_db():
    """
    Connects to the sqlite3 database. Database name is specified within settings
    dictionary (settings.settings["database_name"]).
    """
    return sqlite3.connect(app.config["database_name"])


@app.before_request
def before_request():
    """
    Connects to the database just before any request is started.
    """
    g.db = connect_db()
    g.db.row_factory = sqlite3.Row


@app.teardown_request
def teardown_request(exception):
    """
    As soon as request is finished, it closes the connection with database.
    WARNING: this function DOES NOT commit any changes! You should commit them
    in your views.
    """
    g.db.close()


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


@app.route("/list_plugins")
def list_plugins():
    """
    Return JSONified list of plugins enabled in the collectd's configuration file.
    """
    try:
        config_file = app.config["collectd_config"]
        lines = [line[11:] for line in open(config_file, "r").readlines()
                if line.startswith("LoadPlugin ")]
        return json.dumps(lines)
    except OSError:
        return ("Collectd's configuration file `%s` was not found" % config_file, 404)


@app.route("/list_types")
def list_types():
    """
    Return JSONified list of collectd's types (ie. ways the measured metrics are
    stored in RRDfiles, basic ones are: gauge, derive, counter, absolute.)
    The list is from collectd's main `types.db` file (usually from
    /usr/share/collectd/)
    """
    try:
        types_file = app.config["collectd_types_db"]
        lines = re.findall(r'^(\w+).+$', open(types_file, "r").read(),
                flags=re.U | re.M | re.I)
        return json.dumps(lines)
    except OSError:
        return ("Collectd's file containing types `%s` was not found" % types_file, 404)


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


class ThresholdAPI(MethodView):
    def post(self):
        """
        Adds a threshold to the database. Supports only POST method.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `warning_min`,
            `warning_max`, `failure_min`, `failure_max`, `percentage`,
            `inverted`, `hits`, `hysteresis`
        """
        data = request.form["threshold"]

        fields = ["host", "plugin", "plugin_instance", "type", "type_instance",
                "warning_min", "warning_max", "failure_min", "failure_max",
                "percentage", "inverted", "hits", "hysteresis", ]

        query = "INSERT INTO thresholds ("
        query += ", ".join(fields)
        query += ") VALUES ("
        query += ", ".join(["?"] * len(fields))
        query += ")"

        cursor = g.db.execute(query, [data.get(key, None) for key in fields])
        g.db.commit()

        response = make_response("Threshold added.", 201)
        response.headers["Location"] = url_for("threshold", id=cursor.lastrowid)
        return response

    def get(self, id):
        """
        Obtain threshold selected by `id`.
        """
        query = "SELECT * FROM thresholds WHERE id=?"
        result = g.db.execute(query, [id]).fetchall()

        return json.dumps([OrderedDict(row) for row in result])

    def put(self, id):
        """
        Updates the threshold's record in the database. `id` specifies record.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `warning_min`,
            `warning_max`, `failure_min`, `failure_max`, `percentage`,
            `inverted`, `hits`, `hysteresis`
        """
        data = request.form["threshold"]

        fields = ["host", "plugin", "plugin_instance", "type", "type_instance",
                "warning_min", "warning_max", "failure_min", "failure_max",
                "percentage", "inverted", "hits", "hysteresis", ]

        query = "UPDATE thresholds SET "
        query += ", ".join(key + "=:" + key for key in fields)
        query += "WHERE id=:id"
        data["id"] = id

        try:
            g.db.execute(query, data)

        except sqlite3.Error, e:
            g.db.rollback()
            return ("Error occured: %s" % e, 500)

        else:
            g.db.commit()
            return ("Threshold updated.", 200)

    def delete(self, id):
        """
        Removes the threshold specified by `id`.
        """
        query = "DELETE FROM thresholds WHERE id=?"
        try:
            g.db.execute(query, [id])
        except sqlite3.Error, e:
            g.db.rollback()
            return ("Error occured: %s" % e, 500)
        else:
            g.db.commit()
            return ("Threshold removed.", 200)

thresholds_view = ThresholdAPI.as_view("threshold")
app.add_url_rule("/threshold/", methods=["POST"], defaults={"id": None}, view_func=thresholds_view)
app.add_url_rule("/threshold/<int:id>", methods=["GET", "PUT", "DELETE"], view_func=thresholds_view)


@app.route("/lookup_threshold/<host>/<plugin>/<plugin_instance>/<type>/<type_instance>/")
def lookup_threshold(host, plugin, plugin_instance, type, type_instance):
    """
    Looks up a threshold in the database with similar parameters to the given
    one.
    Only thresholds with the same `type` will be looked up!
    Sorting is based on the number of fields matching given parameters.
    """
    # TODO: test accuracy of this sorting
    def match(row):
        r = 0
        if row["host"] == host:
            r += 4
        if row["plugin"] == plugin:
            r += 2
        if row["plugin_instance"] == plugin_instance:
            r += 1
        if row["type_instance"] == type_instance:
            r += 8
        return r

    host = None if host == "-" else host
    plugin = None if plugin == "-" else plugin
    plugin_instance = None if plugin_instance == "-" else plugin_instance
    type_instance = None if type_instance == "-" else type_instance

    query = "SELECT * FROM thresholds WHERE type=?"
    result = g.db.execute(query, [type, ]).fetchall()

    result.sort(key=match)

    return json.dumps([OrderedDict(row) for row in result])


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
