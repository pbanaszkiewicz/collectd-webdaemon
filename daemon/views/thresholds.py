# coding: utf-8

import simplejson as json
from sqlalchemy.exc import SQLAlchemyError

from flask import Blueprint, current_app, request, url_for, jsonify
from flask import make_response
from flask.views import MethodView
thresholds = Blueprint('thresholds', __name__)

from daemon.models import Threshold
from daemon.database import db


class ThresholdAPI(MethodView):
    def post(self):
        """
        Adds a threshold to the database. Supports only POST method.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `dataset`,
            `warning_min`, `warning_max`, `failure_min`, `failure_max`,
            `percentage`, `inverted`, `hits`, `hysteresis`
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
        #from collections import OrderedDict
        #result = Threshold.query.get_or_404(threshold_id)
        #return jsonify(threshold=OrderedDict(result.items()))
        result = Threshold.query.get_or_404(threshold_id)
        return jsonify(threshold=result.serialized)

    def put(self, threshold_id):
        """
        Updates the threshold's record in the database. `id` specifies record.
        Request body should be a JSON dictionary {"threshold": data}
        `data` should be a dictionary with these keys: `host`, `plugin`,
            `plugin_instance`, `type`, `type_instance`, `dataset`,
            `warning_min`, `warning_max`, `failure_min`, `failure_max`,
            `percentage`, `inverted`, `hits`, `hysteresis`
        """
        data = json.loads(request.form["threshold"])

        try:
            threshold = Threshold.query.get(threshold_id)
            for key, value in data.items():
                setattr(threshold, key, value)
            current_app.db.session.add(threshold)

        except SQLAlchemyError, e:
            current_app.db.session.rollback()
            return ("Error occured: %s" % e, 500)

        else:
            current_app.db.session.commit()
            return ("Threshold updated.", 200)

    def delete(self, threshold_id):
        """
        Removes the threshold specified by `id`.
        """
        try:
            threshold = Threshold.query.get(threshold_id)
            current_app.db.session.delete(threshold)
        except SQLAlchemyError, e:
            current_app.db.session.rollback()
            return ("Error occured: %s" % e, 500)
        else:
            current_app.db.session.commit()
            return ("Threshold removed.", 200)


thresholds_view = ThresholdAPI.as_view("threshold")
thresholds.add_url_rule("/threshold", methods=["POST"],
        view_func=thresholds_view)
thresholds.add_url_rule("/threshold/<int:threshold_id>", methods=["GET", "PUT",
        "DELETE"], view_func=thresholds_view)


@thresholds.route("/lookup_threshold/<host>/<plugin>/<plugin_instance>/<type>/<type_instance>/")
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
        if row.host == host:
            r += 4
        if row.plugin == plugin:
            r += 2
        if row.plugin_instance == plugin_instance:
            r += 1
        if row.type_instance == type_instance:
            r += 8
        return r

    host = None if host == "-" else host
    plugin = None if plugin == "-" else plugin
    plugin_instance = None if plugin_instance == "-" else plugin_instance
    type_instance = None if type_instance == "-" else type_instance

    result = Threshold.query.order_by(Threshold.id)
    result.sort(key=match)

    return jsonify(thresholds=result)
