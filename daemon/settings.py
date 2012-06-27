# TODO: add comments
settings = {
    "DEBUG": True,
    "debug_address": ["0.0.0.0", 8888],
    "collectd_directory": "/var/lib/collectd/",
    "collectd_config": "/etc/collectd/collectd.conf",
    "collectd_types_db": "/usr/share/collectd/types.db",
    "collectd_threshold_file": "thresholds.conf",
    "GWM_host": ["127.0.0.1", ],
    "SQLALCHEMY_DATABASE_URI": "sqlite:///thresholds.db",
    "default_start_time": "-1h",
    "default_end_time": "now",
}
