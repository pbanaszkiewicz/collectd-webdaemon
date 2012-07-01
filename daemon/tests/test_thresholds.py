# coding: utf-8

from __future__ import with_statement
from daemon.tests.base_test import TestCase
import simplejson as json
import os
import shutil

from daemon import settings, create_app
from daemon.database import db
from daemon.models import Threshold


class ThresholdsTestCase(TestCase):
    def create_app(self):
        settings.settings["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
        settings.settings["TESTING"] = True
        return create_app(settings.settings)

    def setUp(self):
        new_path = os.path.join(os.path.dirname(
            self.app.config["collectd_threshold_file"]), "tests",
            "threshold.conf")
        shutil.copyfile(self.app.config["collectd_threshold_file"], new_path)
        self.app.config["collectd_threshold_file"] = new_path
        db.create_all()

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
        * 200 OK
        * 404 Not Found
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

        received = self.client.get("/threshold/2")
        self.assertEqual(received.status_code, 404)
        self.assertEqual(Threshold.query.count(), 1)

    def test_threshold_put(self):
        """
        Test: ThresholdAPI.put, PUT /threshold/<threshold_id>
        * 200 OK when updated
        * 404 when not found
        * 400 when malformed request
        * 400 when some error occured
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
        obj = Threshold(**data)
        db.session.add(obj)
        db.session.commit()
        self.assertEqual(Threshold.query.count(), 1)

        update = {
            "warning_min": 70,
            "invert": True,
            "hits": 2
        }
        received = self.client.put("/threshold/1",
            data=dict(threshold=json.dumps(update)))
        self.assertEqual(received.status_code, 200)

        obj = Threshold.query.get(1)
        for key, value in data.items():
            self.assertEqual(getattr(obj, key), value)

        received = self.client.put("/threshold/123456789",
            data=dict(threshold=json.dumps(update)))
        self.assertEqual(received.status_code, 404)

        received = self.client.put("/threshold/1",
            data=dict(threshold="foobar"))
        self.assertEqual(received.status_code, 400)

        received = self.client.put("/threshold/1",
            data=dict(threshold=json.dumps(dict(typo="foobar"))))
        self.assertEqual(received.status_code, 400)

    def test_threshold_delete(self):
        """
        Test: ThresholdAPI.delete, DELETE /threshold/<threshold_id>
        * 200 OK when deleted
        * 404 when not found
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
        obj = Threshold(**data)
        db.session.add(obj)
        db.session.commit()
        self.assertEqual(Threshold.query.count(), 1)

        received = self.client.delete("/threshold/1")
        self.assertEqual(received.status_code, 200)
        self.assertEqual(Threshold.query.get(1), None)
        self.assertEqual(Threshold.query.count(), 0)

        received = self.client.delete("/threshold/1")
        self.assertEqual(received.status_code, 404)
        self.assertEqual(Threshold.query.count(), 0)

    def test_lookup_threshold(self):
        """
        Test: lookup_threshold, GET /lookup_threshold/<host>/<plugin>/...
        * sorting algorithm works intuitively
        * empty list is returned as well when nothing matches
        """
        # obj1 is the primary Threshold, we'll be looking up similar thresholds
        # to this
        obj1 = Threshold(host="host1", plugin="plugin1",
                plugin_instance="plugin1inst", type="type1",
                type_instance="type1inst")
        db.session.add(obj1)

        obj2 = Threshold(host="host1", plugin="plugin1",
                plugin_instance="plugin1inst", type="type1",
                type_instance="type1inst")
        db.session.add(obj2)
        obj3 = Threshold(host="host2", plugin="plugin1",
                plugin_instance="plugin1inst", type="type1",
                type_instance="type1inst")
        db.session.add(obj3)
        obj4 = Threshold(plugin="plugin1",
                plugin_instance="plugin1inst", type="type1",
                type_instance="type2inst")
        db.session.add(obj4)
        obj5 = Threshold(plugin="plugin1",
                plugin_instance="plugin1inst", type="type2",
                type_instance="type2inst")
        db.session.add(obj5)

        db.session.commit()

        url = "/lookup_threshold/%s/%s/%s/%s/%s"

        received = self.client.get(url % (obj1.host, obj1.plugin,
            obj1.plugin_instance, obj1.type, obj1.type_instance))
        self.assertEqual(received.status_code, 200)
        self.assertEqual(len(received.json["thresholds"]), 4)

        for index, obj in enumerate([obj1, obj2, obj3, obj4]):
            self.assertEqual(json.loads(json.dumps(obj)),
                received.json["thresholds"][index])

        received = self.client.get(url % ("-", "-", "-", "foobar", "-"))
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.json["thresholds"], [])

    def test_config_threshold(self):
        """
        Test: config_threshold, GET /generate_threshold
        * testing both through request and manually invoking function
        """
        url = "/generate_threshold"
        collectd_threshold_file = self.app.config["collectd_threshold_file"]
        self.app.config["collectd_threshold_file"] += "nonexistent"
        received = self.client.get(url)
        self.assertEqual(received.status_code, 404)

        self.app.config["collectd_threshold_file"] = collectd_threshold_file

        F = open(collectd_threshold_file + ".bak", "w")
        F.close()
        os.chmod(collectd_threshold_file + ".bak", 0000)
        received = self.client.get(url)
        self.assertEqual(received.status_code, 404)
        os.chmod(collectd_threshold_file + ".bak", 0777)
        os.remove(collectd_threshold_file + ".bak")

        received = self.client.get(url)
        self.assertEqual(received.status_code, 500)

        #config_thresholds()
