settings = {
    # Only for development purposes.
    "DEBUG": False,
    "debug_address": ["0.0.0.0", 8888],

    # Production setup
    "address": ["0.0.0.0", 9999],

    # Directory, where all data is collected by the collectd daemon.
    # It should contain "rrd" sub-directory.
    "collectd_directory": "/var/lib/collectd/",

    # Main collectd configuration file. It's used to read the list of enabled
    # plugins. The daemon needs the permission to read it.
    "collectd_config": "/etc/collectd/collectd.conf",

    # Collectd's file containing definitions of types different plugins use.
    # The files is read and those types are extracted.
    "collectd_types_db": "/usr/share/collectd/types.db",

    # File containing thresholds configuration for collectd. It should be in
    # daemon's very own directory (so you should not change it).
    # Additionally, in collectd's main configuration file you should add this
    # line at the very bottom:
    # Include "/path/to/daemon/thresholds.conf"
    "collectd_threshold_file": "thresholds.conf",

    # IP addresses which are allowed to communicate with the daemon.
    # CAUTION: use IP addresses, not host names!
    "GWM_host": ["127.0.0.1", ],

    # Database filename. You should not change it.
    # URL schema:
    #   http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    "SQLALCHEMY_DATABASE_URI": "sqlite:///thresholds.db",

    # These values are passed to rrdtool to fetch (by default) last hour of
    # metrics.
    # Examples and full description of time parameters:
    #   http://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html
    "default_start_time": "-1h",
    "default_end_time": "now",
}
