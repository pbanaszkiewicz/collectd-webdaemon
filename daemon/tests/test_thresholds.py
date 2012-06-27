# coding: utf-8

from daemon import settings, create_app
from daemon.models import Threshold
from daemon.database import db
from flaskext.testing import TestCase
import os
import simplejson as json


class ThresholdsTestCase(TestCase):
    def create_app(self):
        settings.settings["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
        settings.settings["TESTING"] = True
        return create_app(settings.settings)

    def setUp(self):
        db.create_all()
        self.app.config["collectd_directory"] = os.path.dirname(__file__)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_threshold_post(self):
        """
        Test: ThresholdAPI.post, POST /threshold
        * reacts 201 Created and creates thresholds
        * appropriate Location header when 201 Created
        * reacts 400 Bad Request upon malformed request
        """
        self.assertEqual(Threshold.query.count(), 0)

        data1 = {
            "host": "node1.example.org",
            "plugin": "cpu",
            "plugin_instance": "0",
            "type": "cpu",
            "type_instance": "user",
            "warning_max": 85
        }
        received = self.client.post("/threshold",
            data=dict(threshold=json.dumps(data1)), follow_redirects=False)
        self.assertEqual(received.status_code, 201)
        self.assertTrue(received.headers["Location"].endswith("/threshold/1"))

        self.assertEqual(Threshold.query.count(), 1)

        for data in ["foobar", dict(threshold="{}"),
                dict(threshold=json.dumps(dict(typo="foobar")))]:
            received = self.client.post("/threshold",
                data=data)
            self.assertEqual(received.status_code, 400)
            self.assertEqual(Threshold.query.count(), 1)

    def test_threshold_get(self):
        """
        Test: ThresholdAPI.get, GET /threshold/<threshold_id>
        * reacts 201 Created and creates thresholds
        * appropriate Location header when 201 Created
        * reacts 400 Bad Request upon malformed request
        """
        self.assertEqual(Threshold.query.count(), 0)
        data = {
            "host": "node1.example.org",
            "plugin": "cpu",
            "plugin_instance": "0",
            "type": "cpu",
            "type_instance": "user",
            "warning_max": 85
        }
        received = self.client.post("/threshold",
                data=dict(threshold=json.dumps(data)))

        self.assertEqual(Threshold.query.count(), 1)

        received = self.client.get("/threshold/1")
        self.assertEqual(received.status_code, 200)
        for key, value in data.items():
            self.assertEqual(received.json["threshold"][key], value)
