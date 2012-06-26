# coding: utf-8
import re
import rrdtool
import os


def read_rrd(data_dir, paths, start, end):
    """
    Return a dictionary of pairs RRD file name and it's parsed content.

    Actually supports only first value, even though RRD file can store more at
    one frame.

    Supports many RRD files (needs to have full host/plugin/rrdfile paths
    provided.)
    """
    return_data = dict()

    try:
        for path in paths:
            rrd_file = os.path.join(data_dir, path)

            data = rrdtool.fetch(str(rrd_file), "AVERAGE", "-s", start, "-e",
                    end)

            return_data[path] = list()

            for dataset, dataset_name in enumerate(data[1]):
                # iterating through possible datasets
                D = list()
                for k, v in enumerate(data[2]):
                    # time is being multiplied by 1000, because JS handles EPOCH
                    # as miliseconds, not seconds since 1/1/1970 00:00:00

                    #        [ time                               , value]
                    D.append([(data[0][0] + data[0][2] * k) * 1000, v[dataset]])

                return_data[path].append(
                    {
                    "label": os.path.basename(path) + " (%s)" % dataset_name,
                    "data": D
                    }
                )

        return (200, return_data)

    except OSError:
        return (404, rrd_file)

    except rrdtool.error, e:
        return (500, str(e))


def collectd_to_XML(config):
    """
    Change collectd's configuration format to XML (because they're very similar).

    :param config:  Collectd's configuration
    """
    # XXX: possibly deprecate this, as I can generate JSON from database and
    #      send it to the browser
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
