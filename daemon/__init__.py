# coding: utf-8

from __future__ import with_statement
import os.path
from flask import Flask, request, abort
import warnings
from sqlalchemy.exc import SAWarning


def create_app(config):
    # I want to handle all SQLAlchemy warnings as exceptions
    warnings.simplefilter("error", SAWarning)

    # setting default accepted IP addresses
    config["GWM_host"] = config.get("GWM_host", ["127.0.0.1", ])

    # setting full paths
    config["collectd_threshold_file"] = config.get("collectd_threshold_file",
            "thresholds.conf")
    config["collectd_threshold_file"] = os.path.join(os.path.dirname(__file__),
            config["collectd_threshold_file"])

    app = Flask(__name__)
    app.config.update(config)

    from daemon.database import db
    db.init_app(app)
    with app.test_request_context():
        from daemon.models import Threshold
        db.create_all()

    from views.metrics import metrics
    from views.thresholds import thresholds

    app.register_blueprint(metrics)
    app.register_blueprint(thresholds)

    @app.before_request
    def before_request():
        """
        Here I abort requests that are not allowed, ie. they're not listed in
        config["GWM_host"] list.
        This function should work not with hostnames, but with IP addresses.
        """
        if not app.debug and request.remote_addr not in app.config["GWM_host"]:
            abort(404)

    return app
