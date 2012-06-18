# coding: utf-8
import re


def filter_dirs(name):
    for i in ["memory", "cpu", "interface", "disk", "net"]:
        if name.startswith(i):
            return True
    return False


def collectd_to_XML(string):
    """
    Change collectd's configuration format to XML (because they're very similar).
    """
    S = re.sub(r'<(\w+) "([^"]+)">', r'<\1 name="\2">', string, flags=re.U | re.I)
    S = re.sub(r"^(\s+)(\w+)\s+(.+)$", r"\1<\2>\3</\2>", S, flags=re.M | re.U | re.I)
    S = re.sub(r'>"([^"]+)"<', r'>\1<', S)
    return S


def XML_to_collectd(string, spacing="  "):
    """
    Change XML to collectd's configuration format.
    """
    S = re.sub(r'<(\w+) name="([^"]+)">', r'<\1 "\2">', string, flags=re.U | re.I)
    S = re.sub(r'<(\w+)>([^<]+)</\1>', r'\1' + spacing + r'\2', S, flags=re.U | re.I)
    S = re.sub(r'^(\s+)(\w+)(\s+)([a-z].+)$', r'\1\2\3"\4"', S, flags=re.U | re.I | re.M)
    return S
