# coding: utf-8

import os
import signal
import shutil
import subprocess
from subprocess import CalledProcessError

import simplejson as json
from sqlalchemy.exc import SQLAlchemyError, SAWarning

from flask import Blueprint, request, url_for, jsonify, make_response
from flask import current_app
from flask.views import MethodView
thresholds = Blueprint('thresholds', __name__)

from daemon.models import Threshold
from daemon.database import db
from daemon.utils import generate_threshold_config


class ThresholdAPI(MethodView):
    def post(self):
        """
        Adds a threshold to the database. Supports only POST method.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `datasource`,
            `warning_min`, `warning_max`, `failure_min`, `failure_max`,
            `percentage`, `invert`, `hits`, `hysteresis`
        Key `type` is mandatory.
        """
        try:
            data = json.loads(request.form["threshold"])
            data["type"]

            threshold = Threshold(**data)
            db.session.add(threshold)

        except (json.JSONDecodeError, KeyError, SQLAlchemyError):
            db.session.rollback()
            return "Malformed request", 400

        else:
            db.session.commit()

            response = make_response("Threshold added.", 201)
            # XXX: url_for() does not make a good URL with provided kwarg
            #      threshold=cursor.lastrowid
            response.headers["Location"] = url_for("thresholds.threshold",
                    _external=False) + "/%s" % threshold.id
            return response

    def get(self, threshold_id):
        """
        Obtain threshold selected by `id`.
        """
        result = Threshold.query.get_or_404(threshold_id)
        return jsonify(threshold=result)

    def put(self, threshold_id):
        """
        Updates the threshold's record in the database. `id` specifies record.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `datasource`,
            `warning_min`, `warning_max`, `failure_min`, `failure_max`,
            `percentage`, `invert`, `hits`, `hysteresis`
        """
        try:
            data = json.loads(request.form["threshold"])
            threshold = Threshold.query.get_or_404(threshold_id)
            threshold.query.update(data)

        except (SQLAlchemyError, SAWarning, json.JSONDecodeError):
            db.session.rollback()
            return ("Malformed request", 400)

        else:
            db.session.commit()
            return ("Threshold updated.", 200)

    def delete(self, threshold_id):
        """
        Removes the threshold specified by `id`.
        """
        try:
            threshold = Threshold.query.get_or_404(threshold_id)
            db.session.delete(threshold)
        except (SQLAlchemyError, SAWarning):
            db.session.rollback()
            return ("Error occured.", 500)
        else:
            db.session.commit()
            return ("Threshold removed.", 200)


thresholds_view = ThresholdAPI.as_view("threshold")
thresholds.add_url_rule(
    "/threshold",
    methods=["POST"],
    view_func=thresholds_view
)
thresholds.add_url_rule(
    "/threshold/<int:threshold_id>",
    methods=["GET", "PUT", "DELETE"],
    view_func=thresholds_view
)


@thresholds.route("/thresholds/")
def list_thresholds():
    result = Threshold.query.order_by(Threshold.id)
    if result:
        return jsonify(thresholds=list(result))
    else:
        return "Not Found", 404


@thresholds.route("/lookup_threshold/<host>/<plugin>/<plugin_instance>/<type>/<type_instance>")
def lookup_threshold(host, plugin, plugin_instance, type, type_instance):
    """
    Looks up a threshold in the database with similar parameters to the given
    one.
    Only thresholds with the same `type` will be looked up!
    Sorting is based on the number of fields matching given parameters.
    """
    def match(row):
        value = 0
        value += 4 if row.host == host else 0
        value += 2 if row.plugin == plugin else 0
        value += 1 if row.plugin_instance == plugin_instance else 0
        value += 8 if row.type_instance == type_instance else 0
        return value

    host = None if host == "-" else host
    plugin = None if plugin == "-" else plugin
    plugin_instance = None if plugin_instance == "-" else plugin_instance
    type_instance = None if type_instance == "-" else type_instance

    result = Threshold.query.filter(Threshold.type == type)
    result = list(result)
    result.sort(key=match, reverse=True)

    return jsonify(thresholds=result)


@thresholds.route("/generate_threshold")
def config_thresholds(pid=None):
    """
    Saves data from database into the file (set up in
    settings.settings["collectd_threshold_file"].)
    After successful save, restarts the server.
    """
    # backup current config
    filename = current_app.config.get("collectd_threshold_file",
        "thresholds.conf")
    filename = os.path.join(os.path.dirname(__file__), filename)
    backup = filename + ".bak"
    try:
        shutil.copyfile(filename, backup)
    except IOError:
        return "Configuration file not spotted.", 404

    result_set = Threshold.query.order_by(Threshold.host). \
            order_by(Threshold.plugin).order_by(Threshold.type). \
            order_by(Threshold.id)

    try:
        F = open(filename, "w")
        F.write(generate_threshold_config(result_set))
        F.close()

    except IOError:
        shutil.move(backup, filename)
        return "Cannot save file.", 404

    try:
        # test if the new config works
        result = subprocess.check_output(["collectd", "-t"])

        if result:
            # unfortunately there might be errors, even though process' return
            # code is 0. But possible errors appear in the output, so we check
            # if it exists
            raise CalledProcessError("Should be no output", 1)

    except (CalledProcessError, OSError):
        # restore backup in case of failure
        shutil.move(backup, filename)
        return "Something in config is wrong, reverting.", 500

    else:
        os.remove(backup)

        # restart the server in case of success
        try:
            pid = pid or subprocess.check_output(["pidof",
                "collectdmon"]).strip().split()[0]
        except subprocess.CalledProcessError:
            return "Cannot restart collectd daemon. You should restart it " + \
                   "manually on your own.", 200
        else:
            os.kill(int(pid), signal.SIGHUP)
            return "Configuration updated, server restarted.", 200
