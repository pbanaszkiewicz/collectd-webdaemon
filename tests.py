# coding: utf-8

import unittest
from xml.dom.minidom import parseString as parse_XML
from utils import filter_dirs, collectd_to_XML, XML_to_collectd


class UtilitiesTestCase(unittest.TestCase):
    """
    This class performs testing upon `utils.py` module containing:
        * filtering metrics function
        * converting configuration to / from XML functions
    """

    def test_filter_dirs(self):
        for name in ["memory_test", "cpu_arg", "interface-eth0", "disk-io", "net_bubble"]:
            self.assertTrue(filter_dirs(name))

        for wrong_name in ["harakiri", "gpu", "sensor", "xkcd"]:
            self.assertFalse(filter_dirs(wrong_name))

    def test_collectd_to_XML(self):
        config1 = """
        # dummy comment
            <Host "hostname">
                SomeValue "foobar"

                DecValue 1000.01
            </Host>
        """
        result1 = collectd_to_XML(config1)
        parse_XML(result1)
        self.assertEqual(result1.strip(),
            """<Host name="hostname">
                <SomeValue>foobar</SomeValue>
                <DecValue>1000.01</DecValue>
            </Host>""")

    def test_XML_to_collectd(self):
        spacing = " "
        config = """<Host name="hostname">
                <SomeValue>foobar</SomeValue>
                <DecValue>1000.01</DecValue>
            </Host>"""
        parse_XML(config)
        result = XML_to_collectd(config, spacing)
        self.assertEqual(result.strip(),
            """<Host "hostname">
                SomeValue "foobar"
                DecValue 1000.01
            </Host>""")
