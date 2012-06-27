# coding: utf-8
from daemon.database import db


class Threshold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(50))
    plugin = db.Column(db.String(50))
    plugin_instance = db.Column(db.String(50))
    type = db.Column(db.String(50), nullable=True)
    type_instance = db.Column(db.String(50))
    dataset = db.Column(db.String(50))
    warning_min = db.Column(db.Float)
    warning_max = db.Column(db.Float)
    failure_min = db.Column(db.Float)
    failure_max = db.Column(db.Float)
    percentage = db.Column(db.Boolean)
    inverted = db.Column(db.Boolean)
    hits = db.Column(db.Integer)
    hysteresis = db.Column(db.Float)

    #def __init__(self, type, host=None, plugin=None, plugin_instance=None,
    #        type_instance=None, dataset=None, warning_min=None,
    #        warning_max=None, failure_min=None, failure_max=None,
    #        percentage=None, inverted=None, hits=None, hysteresis=None):
    #    self.host = host
    #    self.plugin = plugin
    #    self.plugin_instance = plugin_instance
    #    self.type = type
    #    self.type_instance = type_instance
    #    self.dataset = dataset
    #    self.warning_min = warning_min
    #    self.warning_max = warning_max
    #    self.failure_min = failure_min
    #    self.failure_max = failure_max
    #    self.percentage = percentage
    #    self.inverted = inverted
    #    self.hits = hits
    #    self.hysteresis = hysteresis

    @property
    def serialized(self):
        return dict(id=self.id, host=self.host, plugin=self.plugin,
            plugin_instance=self.plugin_instance, type=self.type,
            type_instance=self.type_instance, dataset=self.dataset,
            warning_min=self.warning_min, warning_max=self.warning_max,
            failure_min=self.failure_min, failure_max=self.failure_max,
            percentage=self.percentage, inverted=self.inverted, hits=self.hits,
            hysteresis=self.hysteresis)

    def __repr__(self):
        return "<Threshold(%s, %s, %s, %s, %s)>" % (self.host, self.plugin,
                self.plugin_instance, self.type, self.type_instance)
