# coding: utf-8

from __future__ import with_statement
from flask import Flask
import warnings
from sqlalchemy.exc import SAWarning


def create_app(config):
    # I want to handle all SQLAlchemy warnings as exceptions
    warnings.simplefilter("error", SAWarning)

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

    return app
