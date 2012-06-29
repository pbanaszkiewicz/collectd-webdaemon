# coding: utf-8

from __future__ import with_statement
from flask import Flask, request, abort
import warnings
from sqlalchemy.exc import SAWarning


def create_app(config):
    # I want to handle all SQLAlchemy warnings as exceptions
    warnings.simplefilter("error", SAWarning)

    # settings default accepted IP addresses
    config["GWM_host"] = config.get("GWM_host", ["127.0.0.1", ])

    app = Flask(__name__)
    app.config.update(config)

    from daemon.database import db
    #db.app = app
    db.init_app(app)
    with app.test_request_context():
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
        if request.remote_addr not in app.config["GWM_host"]:
            abort(404)

    return app
