# coding: utf-8
import re


def filter_dirs(name):
    for i in ["memory", "cpu", "interface", "disk", "net"]:
        if name.startswith(i):
            return True
    return False


def collectd_to_XML(config):
    """
    Change collectd's configuration format to XML (because they're very similar).

    :param config:  Collectd's configuration
    """
    # TODO: possibly deprecate this, as I can generate JSON from database and
    #       send it to the browser
    S = config

    replaces = [
        [r'#.*$', r'', re.M],  # drop comments
        [r"\n\n", r"\n", None],  # drop empty lines
        [r'<(\w+) "([^"]+)">', r'<\1 name="\2">', None],  # add attribute `name`
        [r"^(\s+)(\w+)\s+(.+)$", r"\1<\2>\3</\2>", re.M],  # change Value XYZ -> <Value>XYZ</Value>
        [r'>"([^"]+)"<', r'>\1<', None],  # "asd" -> asd
        [r"\s*<([^ >]+)([^>]*)>\r?\n\s*</\1>", r'<\1\2 />', None],  # combine empty entries <a></a> -> <a />
    ]

    for r1, r2, flags in replaces:
        S = re.sub(r1, r2, S, flags=re.U | re.I | (flags if flags else 0))

    return S


def XML_to_collectd(config, spacing="  "):
    """
    Change XML to collectd's configuration format.

    :param config:   XML-ified collectd's configuration
    :param spacing:  default gap between argument name and its value
    """
    # XXX: DEPRECATED since I'll be using sqlite to store all the information
    #      convert them to collectd's configuration file
    S = config

    # remove attribute `name`
    S = re.sub(r'<(\w+) name="([^"]+)">', r'<\1 "\2">', S, flags=re.U | re.I)

    # change <Value>XYZ</Value> -> Value/:param :spacing/XYZ
    S = re.sub(r'<(\w+)>([^<]+)</\1>', r'\1' + spacing + r'\2', S, flags=re.U | re.I)

    # add "" around non-digit values
    S = re.sub(r'^(\s+)(\w+)(\s+)([a-z].+)$', r'\1\2\3"\4"', S, flags=re.U | re.I | re.M)

    # drop empty entries
    S = re.sub(r'\s*<([^>]+)/>', r'', S, flags=re.U | re.I)  # drop empty entries

    return S
