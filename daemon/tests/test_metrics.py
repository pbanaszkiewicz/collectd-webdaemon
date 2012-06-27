# coding: utf-8

from daemon import settings, create_app
from daemon.database import db
from flaskext.testing import TestCase
import os.path
import simplejson as json


class MetricsTestCase(TestCase):
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

    def test_list_hosts(self):
        """
        Test: list_hosts, /list_hosts
        * 200 OK, content
        * 404 Not Found
        """
        received = self.client.get("/list_hosts")
        self.assertEqual(received.status_code, 200)
        self.assertIn("hosts", received.json.keys())
        self.assertEqual(
            set(received.json["hosts"]),
            set(["node1.example.org", "kvm_instance1.example.org"])
        )

        self.app.config["collectd_directory"] += "/.."
        received = self.client.get("/list_hosts")
        self.assertEqual(received.status_code, 404)

    def test_list_plugins(self):
        """
        Test: list_plugins, /list_plugins
        * 200 OK, content
        * 404 Not Found
        """
        self.app.config["collectd_config"] = os.path.join(
            os.path.dirname(__file__), "collectd.conf"
        )
        received = self.client.get("/list_plugins")
        self.assertEqual(received.status_code, 200)
        self.assertIn("plugins", received.json.keys())
        self.assertEqual(
            set(received.json["plugins"]),
            set(["cpu", "memory", "disk", "python", "interface", "rrdtool",
                "kvm_cpu", "kvm_io", "kvm_net", "kvm_memory"])
        )

        self.app.config["collectd_config"] += "nonexistant"
        received = self.client.get("/list_plugins")
        self.assertEqual(received.status_code, 404)

    def test_list_types(self):
        """
        Test: list_types, /list_types
        * 200 OK, content
        * 404 Not Found
        """
        self.app.config["collectd_types_db"] = os.path.join(
            os.path.dirname(__file__), "types.db"
        )
        received = self.client.get("/list_types")
        self.assertEqual(received.status_code, 200)
        self.assertIn("types", received.json.keys())
        self.assertEqual(
            set(received.json["types"]),
            set(["absolute", "dns_rcode", "dns_reject", "dns_request",
                "dns_resolver", "dns_response", "dns_transfer",
                "memcached_command", "ps_state", "pinba_view"])
        )

        self.app.config["collectd_types_db"] += "nonexistant"
        received = self.client.get("/list_types")
        self.assertEqual(received.status_code, 404)

    def test_list_metrics(self):
        """
        Test: list_metrics, /host/<hostname>/list_metrics
        * proper hostname 200 OK, content
        * wrong hostname 404 Not Found
        """
        received = self.client.get("/host/node1.example.org/list_metrics")
        self.assertEqual(received.status_code, 200)
        self.assertIn("metrics", received.json.keys())
        self.assertEqual(
            set(received.json["metrics"]),
            set(["cpu-0", "memory", "interface", "disk-sda"])
        )

        received = self.client.get("/host/fake_node/list_metrics")
        self.assertEqual(received.status_code, 404)

    def test_list_rrds(self):
        """
        Test: list_rrds, /host/<hostname>/list_rrds/<metric>
        * proper hostname and metric 200 OK, content
        * wrong hostname 404 Not Found
        * wrong metric 404 Not Found
        """
        received = self.client.get("/host/node1.example.org/list_rrds/interface")
        self.assertEqual(received.status_code, 200)
        self.assertIn("rrds", received.json.keys())
        self.assertEqual(
            set(received.json["rrds"]),
            set(["if_errors-lo.rrd", "if_packets-lo.rrd", "if_octets-lo.rrd",
                "if_errors-br0.rrd", "if_packets-br0.rrd", "if_octets-br0.rrd"])
        )

        received = self.client.get("/host/fake_node/list_rrds/interface")
        self.assertEqual(received.status_code, 404)

        received = self.client.get("/host/node1.example.org/list_rrds/fake_metric")
        self.assertEqual(received.status_code, 404)

    def test_get_arbitrary_data(self):
        """
        Test: get_arbitrary_data, POST /get/, POST /get/<start>/<end>
        * reacts to proper JSON dictionary
        * reacts to proper JSON array
        * the same RRD paths are in request as in response
        * throws 400 Bad Request upon malformed request
        * DOES NOT test returning correct values!!! Such test in test_utils.py
        """
        data1 = {
            "node1.example.org": {
                "cpu-0": [
                    "cpu-idle.rrd",
                    "cpu-user.rrd",
                ],
                "memory": [
                    "memory-used.rrd",
                    "memory-free.rrd",
                ]
            },
            "kvm_instance1.example.org": {
                "memory_kvm": [
                    "bytes-memory-usage.rrd",
                ],
            }
        }

        data2 = [
            "node1.example.org/cpu-0/cpu-idle.rrd",
            "node1.example.org/cpu-0/cpu-user.rrd",
            "node1.example.org/memory/memory-used.rrd",
            "node1.example.org/memory/memory-free.rrd",
            "kvm_instance1.example.org/memory_kvm/bytes-memory-usage.rrd",
        ]

        received = self.client.post("/get/", data=dict(rrds=json.dumps(data1)))
        self.assertEqual(received.status_code, 200)
        self.assertEqual(set(data2), set(received.json.keys()))

        received = self.client.post("/get/", data=dict(rrds=json.dumps(data2)))
        self.assertEqual(received.status_code, 200)
        self.assertEqual(set(data2), set(received.json.keys()))

        received = self.client.post("/get/", data=dict(foobar=json.dumps(dict())))
        self.assertEqual(received.status_code, 400)

        received = self.client.post("/get/", data=dict(rrds="foobar"))
        self.assertEqual(received.status_code, 400)
