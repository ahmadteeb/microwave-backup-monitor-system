from datetime import datetime
from app.extensions import db

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
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, server_default='1', default=True)

    ping_results = db.relationship('PingResult', backref='link', lazy='dynamic', cascade='all, delete-orphan')
    metrics = db.relationship('MetricSnapshot', backref='link', lazy='dynamic', cascade='all, delete-orphan')
    status = db.relationship('LinkStatus', backref='link', uselist=False, cascade='all, delete-orphan')

class PingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('link.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    reachable = db.Column(db.Boolean, nullable=False)
    latency_ms = db.Column(db.Float, nullable=True)
    packet_loss = db.Column(db.Float, nullable=True)
    raw_output = db.Column(db.Text, nullable=True)
    triggered_by = db.Column(db.String(20), nullable=False, server_default='scheduler', default='scheduler')
    triggered_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

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
    password_encrypted = db.Column(db.String(500), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    label = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class SetupState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_complete = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    completed_at = db.Column(db.DateTime, nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum('admin', 'operator', 'viewer', name='user_roles'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    is_locked = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    locked_until = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    force_password_change = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    permissions = db.relationship('UserPermission', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notification_subscriptions = db.relationship('NotificationSubscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('InAppNotification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    updated_smtp_configs = db.relationship('SmtpConfig', backref='updated_by', foreign_keys='SmtpConfig.updated_by_id')
    updated_jumpservers = db.relationship('JumpServer', backref='updated_by', foreign_keys='JumpServer.updated_by_id')
    updated_app_settings = db.relationship('AppSettings', backref='updated_by', foreign_keys='AppSettings.updated_by_id')

class UserPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission_key = db.Column(db.String(64), nullable=False)
    is_granted = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'permission_key', name='uq_user_permission'),
    )

class NotificationSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_key = db.Column(db.String(64), nullable=False)
    is_subscribed = db.Column(db.Boolean, nullable=False, default=True, server_default='1')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_key', name='uq_user_notification_subscription'),
    )

class InAppNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_key = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.Enum('critical', 'warning', 'info', 'error', name='notification_severity'), nullable=False)
    link_id = db.Column(db.String(32), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class SmtpConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(256), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(256), nullable=True)
    password_encrypted = db.Column(db.String(500), nullable=True)
    from_address = db.Column(db.String(256), nullable=False)
    use_tls = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    use_ssl = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    category = db.Column(db.String(128), nullable=False)
    event = db.Column(db.String(128), nullable=False)
    actor = db.Column(db.String(128), nullable=True)
    target = db.Column(db.String(256), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_timeout_minutes = db.Column(db.Integer, nullable=False, default=480, server_default='480')
    ping_interval_seconds = db.Column(db.Integer, nullable=False, default=60, server_default='60')
    ping_count = db.Column(db.Integer, nullable=False, default=3, server_default='3')
    ping_timeout_seconds = db.Column(db.Integer, nullable=False, default=2, server_default='2')
    consecutive_timeout_alert_threshold = db.Column(db.Integer, nullable=False, default=5, server_default='5')
    util_warning_threshold_pct = db.Column(db.Float, nullable=False, default=70.0, server_default='70.0')
    util_critical_threshold_pct = db.Column(db.Float, nullable=False, default=90.0, server_default='90.0')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class LinkStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey('link.id'), nullable=False, unique=True)
    mw_status = db.Column(db.Enum('up', 'down', 'high', 'checking', 'unknown', name='link_status_enum'), nullable=False, default='unknown', server_default='unknown')
    last_ping_at = db.Column(db.DateTime, nullable=True)
    last_ping_latency_ms = db.Column(db.Float, nullable=True)
    consecutive_timeouts = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    last_metric_at = db.Column(db.DateTime, nullable=True)
    fiber_util_pct = db.Column(db.Float, nullable=True)
    mw_util_pct = db.Column(db.Float, nullable=True)
    last_mw_down_notified_at = db.Column(db.DateTime, nullable=True)
    last_fiber_high_notified_at = db.Column(db.DateTime, nullable=True)
    last_mw_high_notified_at = db.Column(db.DateTime, nullable=True)
    last_fiber_near_cap_notified_at = db.Column(db.DateTime, nullable=True)

# Indexes for performance on history queries

db.Index('idx_ping_result_link_time', PingResult.link_id, PingResult.timestamp.desc())
db.Index('idx_metric_link_time', MetricSnapshot.link_id, MetricSnapshot.timestamp.desc())
