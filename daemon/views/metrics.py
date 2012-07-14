# coding: utf-8

import os
import re
import simplejson as json
from collections import OrderedDict

from flask import current_app, Blueprint, jsonify, request
metrics = Blueprint('metrics', __name__)

from daemon.utils import read_rrd


@metrics.route("/list_tree")
def list_tree():
    """
    Return JSONified tree structure of collectd data directory.
    """
    try:
        data_dir = current_app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")

        tree = OrderedDict()

        walking_dead = os.walk(data_dir)
        hosts = next(walking_dead)[1]

        for host in hosts:
            tree[host] = OrderedDict()
            plugins = next(walking_dead)[1]
            for plugin in plugins:
                types = next(walking_dead)[2]
                tree[host][plugin] = types

        return jsonify(tree=tree)

    except (OSError, StopIteration):
        return ("Collectd directory `%s` not found" % data_dir, 404)


@metrics.route("/list_hosts")
def list_hosts():
    """
    Return JSONified list of all hosts whose data is being collected by
    collectd.
    """
    try:
        data_dir = current_app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")

        return jsonify(hosts=sorted(os.listdir(data_dir)))
    except OSError:
        return ("Collectd directory `%s` was not found" % data_dir, 404)


@metrics.route("/list_plugins")
def list_plugins():
    """
    Return JSONified list of plugins enabled in the collectd's configuration
    file.
    """
    try:
        config_f = current_app.config["collectd_config"]
        file_lines = open(config_f, "r").readlines()
        lines = [line[11:].strip() for line in file_lines
                if line.startswith("LoadPlugin ")]
        lines += re.findall(r'^\s*Import\s+"([^"]+)"$', "".join(file_lines),
                flags=re.M | re.U)
        return jsonify(plugins=lines)
    except (IOError, OSError):
        return ("Collectd's configuration file `%s` not found" % config_f, 404)


@metrics.route("/list_types")
def list_types():
    """
    Return JSONified list of collectd's types (ie. ways the measured metrics are
    stored in RRDfiles, basic ones are: gauge, derive, counter, absolute.)
    The list is from collectd's main `types.db` file (usually from
    /usr/share/collectd/)
    """
    try:
        types_file = current_app.config["collectd_types_db"]
        lines = re.findall(r'^(\w+).+$', open(types_file, "r").read(),
                flags=re.U | re.M | re.I)
        return jsonify(types=lines)
    except (IOError, OSError):
        return ("Collectd's file containing types `%s` not found" % types_file,
                404)


@metrics.route("/host/<host>/list_metrics")
def list_metrics(host):
    """
    Return JSONified list of directories (which contain RRD files) of particular
    host.
    """
    try:
        data_dir = current_app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)

        return jsonify(metrics=sorted(os.listdir(host_dir)))
    except (IOError, OSError):
        return ("Collectd hostname directory `%s` was not found" % host_dir,
                404)


@metrics.route("/host/<host>/list_rrds/<metrics>")
def list_rrds(host, metrics):
    """
    Return JSONified list of RRD files in particular directory.
    """
    try:
        data_dir = current_app.config["collectd_directory"]
        data_dir = os.path.join(data_dir, "rrd")
        host_dir = os.path.join(data_dir, host)
        metrics_dir = os.path.join(host_dir, metrics)
        return jsonify(rrds=sorted(os.listdir(metrics_dir)))
    except OSError:
        return ("Collectd metrics `%s@%s` were not found" % (metrics, host),
                404)


@metrics.route("/get/", methods=["POST"], defaults={"start": None, "end": None})
@metrics.route("/get/<start>/<end>", methods=["POST"])
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
    try:
        results = json.loads(request.form["rrds"])
    except (json.JSONDecodeError, KeyError):
        return ("Malformed request", 400)

    paths = []

    if isinstance(results, dict):
        # option 1) dict/tree
        # I assume the tree has 3 levels
        for host in results.keys():
            for plugin in results[host].keys():
                for fn in results[host][plugin]:
                    paths.append(os.path.join(host, plugin, fn))
    else:
        # option 2) list
        # simply copy the list
        paths = results[:]

    start = start or current_app.config["default_start_time"]
    end = end or current_app.config["default_end_time"]

    dir_path = os.path.join(current_app.config["collectd_directory"], "rrd")
    data = read_rrd(dir_path, paths, str(start),
            str(end))

    if data[0] == 404:
        return ("Some collectd's metrics were not found: %s" % data[1], 404)

    elif data[0] == 500:
        return ("RRDTool is borked: `%s`" % data[1], 500)

    return jsonify(data[1])
