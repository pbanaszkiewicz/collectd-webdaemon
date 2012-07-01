# coding: utf-8
from daemon.database import db
from collections import OrderedDict


class DictSerializable(object):
    def _asdict(self):
        result = OrderedDict()
        for key in self.__mapper__.c.keys():
            result[key] = getattr(self, key)
        return result


class Threshold(DictSerializable, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(50))
    plugin = db.Column(db.String(50))
    plugin_instance = db.Column(db.String(50))
    type = db.Column(db.String(50), nullable=True)
    type_instance = db.Column(db.String(50))
    datasource = db.Column(db.String(50))
    warning_min = db.Column(db.Float)
    warning_max = db.Column(db.Float)
    failure_min = db.Column(db.Float)
    failure_max = db.Column(db.Float)
    percentage = db.Column(db.Boolean)
    persist = db.Column(db.Boolean)
    invert = db.Column(db.Boolean)
    hits = db.Column(db.Integer)
    hysteresis = db.Column(db.Float)

    def __repr__(self):
        return "<Threshold (%s, %s, %s, %s, %s)>" % (self.host, self.plugin,
                self.plugin_instance, self.type, self.type_instance)
