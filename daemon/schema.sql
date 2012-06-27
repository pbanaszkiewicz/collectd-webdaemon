drop table if exists thresholds;

create table thresholds (
    id integer primary key autoincrement,
    host character(50),
    plugin character(50),
    plugin_instance character(50),
    type character(50) not null,
    type_instance character(50),
    dataset character(50),
    warning_min double,
    warning_max double,
    failure_min double,
    failure_max double,
    percentage boolean,
    inverted boolean,
    hits integer,
    hysteresis double
);
