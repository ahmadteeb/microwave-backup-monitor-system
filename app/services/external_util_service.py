import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from flask import current_app
from app.extensions import db
from app.models import Link, MetricSnapshot, LinkStatus, LegUtilizationSnapshot

logger = logging.getLogger(__name__)
_external_engine = None


def _get_external_engine():
    global _external_engine
    uri = current_app.config.get('SQLALCHEMY_EXTERNAL_UTIL_DATABASE_URI')
    if not uri:
        return None

    if _external_engine is None or str(_external_engine.url) != uri:
        # Ensure driver is instructed to use UTF-8 and return unicode strings
        _external_engine = create_engine(uri, pool_pre_ping=True, connect_args={'charset': 'utf8mb4', 'use_unicode': True})

    return _external_engine


def lookup_link_info(link_id):
    engine = _get_external_engine()
    if engine is None:
        raise RuntimeError('External utilization database is not configured')

    query = text(
        "SELECT Link_Name, Link_Name_Unif, Link_Categ, SiteID, Source_NE_Card, SiteID_Opp, Sink_NE_Card, AVG_MAX_Util_RxTx_perc, AVG_MAX_Rx_Kbps, AVG_MAX_Tx_Kbps, MW_Link_Capacity, XPIC_MW_Link_Capacity "
        "FROM pandq_mw_link_max_week_utilization "
        "WHERE Link_Name = :link_id OR Link_Name_Unif = :link_id LIMIT 1"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {'link_id': link_id}).mappings().first()
        return dict(row) if row else None


def lookup_leg_info(leg_name):
    engine = _get_external_engine()
    if engine is None:
        raise RuntimeError('External utilization database is not configured')

    query = text(
        "SELECT LEG_Name, AVG_MAX_MBitRate, Interface_Speed_Min, Interface_Speed_Max, Sub_LEG_Count "
        "FROM pandq_leg_max_week_utilization "
        "WHERE LEG_Name = :leg_name LIMIT 1"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {'leg_name': leg_name}).mappings().first()
        if not row:
            return None
        result = dict(row)
        try:
            avg_mbit = float(result.get('AVG_MAX_MBitRate') or 0)
            if_speed_max = float(result.get('Interface_Speed_Max') or 0)
            result['LEG_Util_pct'] = round((avg_mbit / if_speed_max) * 100, 1) if if_speed_max > 0 else None
        except (TypeError, ValueError):
            result['LEG_Util_pct'] = None
        return result


def refresh_external_utilization():
    engine = _get_external_engine()
    if engine is None:
        logger.info('External utilization database is not configured, skipping refresh')
        return

    logger.info('Refreshing external utilization data')
    link_rows = Link.query.filter(Link.is_active == True).all()
    for link in link_rows:
        row = lookup_link_info(link.link_id)
        if not row:
            continue

        # Persist external node and legacy link metadata to inventory records.
        if row.get('Source_NE_Card'):
            link.site_a = row.get('Source_NE_Card')
        if row.get('Sink_NE_Card'):
            link.site_b = row.get('Sink_NE_Card')
        if row.get('Link_Name_Unif'):
            link.leg_name = row.get('Link_Name_Unif')

        snapshot = MetricSnapshot(
            link_id=link.id,
            mw_util_pct=row.get('AVG_MAX_Util_RxTx_perc'),
            mw_capacity_mbps=row.get('XPIC_MW_Link_Capacity') if row.get('XPIC_MW_Link_Capacity') is not None else row.get('MW_Link_Capacity'),
            source='external'
        )
        db.session.add(snapshot)

        status = LinkStatus.query.filter_by(link_id=link.id).first()
        if status:
            status.mw_util_pct = snapshot.mw_util_pct
            status.last_metric_at = datetime.utcnow()

    # Refresh aggregated leg metadata files as snapshots for lookup and history.
    leg_names = db.session.query(Link.leg_name).filter(Link.leg_name.isnot(None)).distinct().all()
    for (leg_name,) in leg_names:
        if not leg_name:
            continue
        row = lookup_leg_info(leg_name)
        if not row:
            continue

        leg_snapshot = LegUtilizationSnapshot(
            leg_name=row.get('LEG_Name'),
            avg_max_mbitrate=row.get('AVG_MAX_MBitRate'),
            interface_speed_min=row.get('Interface_Speed_Min'),
            interface_speed_max=row.get('Interface_Speed_Max'),
            sub_leg_count=row.get('Sub_LEG_Count'),
            source='external'
        )
        db.session.add(leg_snapshot)

    db.session.commit()
