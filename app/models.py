from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    leg_name = db.Column(db.String(100), nullable=False, index=True)
    site_a = db.Column(db.String(100), nullable=True)
    site_b = db.Column(db.String(100), nullable=True)
    mw_ip = db.Column(db.String(45), nullable=False)
    equipment_a = db.Column(db.String(100), nullable=True)
    equipment_b = db.Column(db.String(100), nullable=True)
    link_type = db.Column(db.String(50), nullable=True, default='microwave')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    ping_results = db.relationship('PingResult', backref='link', lazy='dynamic', cascade='all, delete-orphan')
    metrics = db.relationship('MetricSnapshot', backref='link', lazy='dynamic', cascade='all, delete-orphan')

class PingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('link.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    reachable = db.Column(db.Boolean, nullable=False)
    latency_ms = db.Column(db.Float, nullable=True)
    packet_loss = db.Column(db.Float, nullable=True)
    raw_output = db.Column(db.Text, nullable=True)

class MetricSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('link.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    fiber_util_pct = db.Column(db.Float, nullable=True)
    fiber_capacity_mbps = db.Column(db.Float, nullable=True)
    mw_util_pct = db.Column(db.Float, nullable=True)
    mw_capacity_mbps = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(20), nullable=True, default='manual')

class JumpServer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=22)
    username = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.String(500), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    label = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

db.Index('idx_ping_result_link_time', PingResult.link_id, PingResult.timestamp.desc())
db.Index('idx_metric_link_time', MetricSnapshot.link_id, MetricSnapshot.timestamp.desc())
