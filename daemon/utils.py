# coding: utf-8
import rrdtool
import os
from daemon.models import Threshold


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


def generate_threshold_config(result_set):
    """
    Generates well-formatted configuration file (with collectd's syntax)
    containing threshold options (also nested ones).
    Does not need any arguments, gathers all entries from database.

    :param result_set: contains result of a SQLAlchemy query.
    """
    map_keys = {
        "type_instance": "Instance",
        #"plugin_instance": "Instance",
        "datasource": "DataSource",
        "warning_min": "WarningMin",
        "warning_max": "WarningMax",
        "failure_min": "FailureMin",
        "failure_max": "FailureMax",
        "percentage": "Percentage",
        "persist": "Persist",
        "invert": "Invert",
        "hits": "Hits",
        "hysteresis": "Hysteresis",
    }
    content = "%s\n%s"

    # XXX: I'm not generating multiple nested plugins/types, because it's not
    #      really needed. Collectd is supposed to understand "straight" options.

    for row in result_set:
        T = 1  # number of tabs in indent
        if row.host:
            host = '\n' + "\t" * T
            host += '<Host "%s">' % row.host
            host += "%s\n" + "\t" * T + "</Host>"
            content = content % (host, "%s")
            T += 1

        if row.plugin:
            plugin = '\n' + "\t" * T
            plugin += '<Plugin "%s">' % row.plugin
            if row.plugin_instance:
                plugin += '\n\t' + "\t" * T
                plugin += 'Instance "%s"\n' % row.plugin_instance
            plugin += "%s\n" + "\t" * T
            plugin += "</Plugin>"
            content = content % (plugin, "%s")
            T += 1

        # generating <Type> tag
        S = "\n" + "\t" * T
        S += '<Type "%s">' % row.type
        S += """
%s
%s
"""
        S += "\n" + "\t" * T + "</Type>"
        T += 1

        for key, value in row._asdict().items():
            if key in map_keys.keys() and value != None:
                if isinstance(value, unicode):
                    v = "\t" * T + "%s \"%s\"" % (map_keys[key], value)
                    S = S % (v, "%s\n%s")
                elif isinstance(value, float):
                    v = "\t" * T + "%s %0.2f" % (map_keys[key], value)
                    S = S % (v, "%s\n%s")
                elif isinstance(value, bool):
                    v = "\t" * T + "%s %s" % (map_keys[key], str(value).lower())
                    S = S % (v, "%s\n%s")
                else:
                    # only integer value is left
                    v = "\t" * T + "%s %s" % (map_keys[key], value)
                    S = S % (v, "%s\n%s")

        S = S.replace("%s\n%s", "")
        S = S.replace("\n\n", "")

        content = content % (S, "%s\n%s")

    content = content.replace("%s\n%s", "")

    return "<Threshold>" + content + "</Threshold>\n"
