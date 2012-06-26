#!/usr/bin/env python
# coding: utf-8

import os
#from xml.dom.minidom import parseString as parse_XML
import re
from collections import OrderedDict

import sqlite3
import simplejson as json

# TODO: switch to flask.jsonify to make good JSON responses
from flask import Flask, g, request, redirect, make_response, url_for
from flask.views import MethodView

from settings import settings
from utils import read_rrd


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
            sorted([d for d in os.listdir(host_dir) if os.path.isdir(os.path.join(host_dir, d))])
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


@app.route("/get/", methods=["POST"], defaults={"start": None, "end": None})
@app.route("/get/<start>/<end>/", methods=["POST"])
def get_arbitrary_data(start, end):
    """
    Returns content of any / many RRD files.
    Works upon POST request, when request body contains a JSONified structure:
        1) tree
            {
                "host1": {"plugin1": {"rrd1", "rrd2"}, "plugin2": {"rrd3",} },
                "host2": {"plugin2": {"rrd1", "rrd2"}, "plugin4": {"rrd3",} }
            }
        2) list
            [
                "host1/plugin1/rrd1",
                "host1/plugin1/rrd2",
                "host1/plugin2/rrd3",
                "host2/plugin2/rrd1",
                "host2/plugin2/rrd2",
                "host2/plugin4/rrd3"
            ]
    This structure has to be in "rrds" POST argument.

    Returns a dictionary, where keys are paths like in above "list" example and
    values are {"label": ..., "data": ...} dicts.
    """
    results = json.loads(request.form["rrds"])

    paths = []

    if isinstance(results, dict):
        # option 1) dict/tree
        # I assume the tree has 3 levels
        for host in results.values():
            for plugin in results[host]:
                for fn in results[host][plugin]:
                    paths.append(os.path.join(host, plugin, fn))
    else:
        # option 2) list
        # simply copy the list
        paths = results[:]

    start = start or app.config["default_start_time"]
    end = end or app.config["default_end_time"]

    data = read_rrd(app.config["collectd_directory"], paths, start, end)

    if data[0] == 404:
        return ("Some collectd's metrics were not found: %s" % data[1], 404)

    elif data[0] == 500:
        return ("RRDTool is borked: `%s`" % data[1], 500)

    return (json.dumps(data[1]), 200)


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

    query = "SELECT id, host, plugin, plugin_instance, type, type_instance "
    query += "FROM thresholds WHERE type=?"
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
