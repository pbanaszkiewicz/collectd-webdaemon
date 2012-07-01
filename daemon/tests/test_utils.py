# coding: utf-8

from daemon.tests.base_test import TestCase
from daemon import settings, create_app
from daemon.database import db
from daemon.models import Threshold
from daemon.utils import generate_threshold_config


class UtilitiesTestCase(TestCase):
    """
    This class performs testing upon `utils.py` module containing:
        * filtering metrics function
        * converting configuration to / from XML functions
    """

    def create_app(self):
        settings.settings["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
        settings.settings["TESTING"] = True
        return create_app(settings.settings)

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_generate_threshold_config(self):
        """
        Test: generate_threshold_config, utility function
        * generates exact config from a given set of thresholds
        """
        obj1 = Threshold(type="counter", warning_min=0, warning_max=1000,
                failure_min=0, failure_max=1200, invert=False, persist=False,
                type_instance="some_instance")
        obj2 = Threshold(type="df", warning_max=90, percentage=True)
        obj3 = Threshold(type="load", datasource="midterm", warning_max=1,
                hysteresis=0.3)
        obj4 = Threshold(type="cpu", type_instance="user", warning_max=85,
                hits=6)
        obj5 = Threshold(plugin="interface", plugin_instance="eth0",
                type="if_octets", datasource="rx", failure_max=10000000)
        obj6 = Threshold(host="hostname", type="cpu", type_instance="idle",
                failure_min=10)
        obj7 = Threshold(host="hostname", plugin="memory", type="memory",
                type_instance="cached", warning_min=100000000)

        for obj in [obj1, obj2, obj3, obj4, obj5, obj6, obj7]:
            db.session.add(obj)
        db.session.commit()

        self.assertEqual(Threshold.query.count(), 7)

        result_set = Threshold.query.order_by(Threshold.host). \
            order_by(Threshold.plugin).order_by(Threshold.type). \
            order_by(Threshold.id)

        with open(self.app.config["collectd_threshold_file"], "r") as f:
            self.assertEqual(f.read(), generate_threshold_config(result_set))
