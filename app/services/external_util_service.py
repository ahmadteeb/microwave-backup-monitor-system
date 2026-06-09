import logging
import traceback
from datetime import datetime
from sqlalchemy import create_engine, text, func
from flask import current_app
from app.extensions import db
from app.models import Link, LinkStatus, ExternalDbConfig

logger = logging.getLogger(__name__)
_external_engine = None

# Module-level error tracking for UI feedback (Tier 2.3)
_last_external_error = None
_last_external_error_at = None


def _get_external_engine():
    global _external_engine
    
    ext_config = ExternalDbConfig.query.filter_by(active=True).first()
    if not ext_config:
        return None
        
    from urllib.parse import quote_plus
    from app.services.crypto_service import decrypt
    
    username = quote_plus(ext_config.username.strip())
    password = ''
    if ext_config.password_encrypted:
        try:
            password = quote_plus(decrypt(ext_config.password_encrypted))
        except Exception as e:
            logger.error(f"Failed to decrypt external DB password: {e}")
            
    host = ext_config.host.strip()
    port = ext_config.port
    database = ext_config.database.strip()
    
    uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    if _external_engine is None or str(_external_engine.url) != uri:
        # Ensure driver is instructed to use UTF-8 and return unicode strings
        _external_engine = create_engine(uri, pool_pre_ping=True, connect_args={'charset': 'utf8mb4', 'use_unicode': True})

    return _external_engine


def invalidate_external_engine():
    global _external_engine
    if _external_engine is not None:
        try:
            _external_engine.dispose()
        except Exception as e:
            logger.warning(f"Error disposing external engine: {e}")
        _external_engine = None


def test_external_connection():
    """
    Test connectivity to the external DB (Tier 2.3).
    
    Returns a dict with 'success' (bool) and 'message' (str).
    Never raises — always returns a result dict.
    """
    try:
        ext_config = ExternalDbConfig.query.filter_by(active=True).first()
        if not ext_config:
            return {'success': False, 'message': 'No active external database configuration found.'}

        from urllib.parse import quote_plus
        from app.services.crypto_service import decrypt

        username = quote_plus(ext_config.username.strip())
        password = ''
        if ext_config.password_encrypted:
            try:
                password = quote_plus(decrypt(ext_config.password_encrypted))
            except Exception as e:
                return {'success': False, 'message': f'Failed to decrypt password: {e}'}

        host = ext_config.host.strip()
        port = ext_config.port
        database = ext_config.database.strip()

        uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        engine = create_engine(
            uri,
            pool_pre_ping=True,
            connect_args={
                'charset': 'utf8mb4',
                'use_unicode': True,
                'connect_timeout': 5
            }
        )
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        engine.dispose()
        return {'success': True, 'message': 'Connected successfully'}
    except Exception as exc:
        return {'success': False, 'message': str(exc)}


def get_external_db_status():
    """
    Return connection status and last sync info for the external DB (Tier 2.3).
    
    Uses max(LinkStatus.last_metric_at) as a proxy for last successful sync time.
    Exposes the last error message from refresh_external_utilization if any.
    """
    global _last_external_error, _last_external_error_at

    try:
        ext_config = ExternalDbConfig.query.filter_by(active=True).first()
        configured = ext_config is not None
    except Exception:
        configured = False

    last_sync = None
    try:
        result = db.session.query(func.max(LinkStatus.last_metric_at)).scalar()
        if result:
            last_sync = result.isoformat() + 'Z'
    except Exception:
        pass

    return {
        'configured': configured,
        'last_sync_at': last_sync,
        'last_error': _last_external_error,
        'last_error_at': _last_external_error_at.isoformat() + 'Z' if _last_external_error_at else None,
    }


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

def refresh_external_utilization_for_single_link(link):
    engine = _get_external_engine()
    if engine is None:
        return

    row = lookup_link_info(link.link_id)
    if row:
        if row.get('Source_NE_Card'):
            link.site_a = row.get('Source_NE_Card')
        if row.get('Sink_NE_Card'):
            link.site_b = row.get('Sink_NE_Card')

        status = LinkStatus.query.filter_by(link_id=link.id).first()
        if not status:
            status = LinkStatus(link_id=link.id)
            db.session.add(status)
            
        status.mw_util_pct = row.get('AVG_MAX_Util_RxTx_perc')
        status.mw_capacity_mbps = row.get('XPIC_MW_Link_Capacity') if row.get('XPIC_MW_Link_Capacity') is not None else row.get('MW_Link_Capacity')
        status.metric_source = 'external'
        status.last_metric_at = datetime.utcnow()

    if link.leg_name:
        leg_row = lookup_leg_info(link.leg_name)
        if leg_row:
            status = LinkStatus.query.filter_by(link_id=link.id).first()
            if not status:
                status = LinkStatus(link_id=link.id)
                db.session.add(status)
            status.avg_max_mbitrate = leg_row.get('AVG_MAX_MBitRate')
            status.interface_speed_min = leg_row.get('Interface_Speed_Min')
            status.interface_speed_max = leg_row.get('Interface_Speed_Max')
            status.sub_leg_count = leg_row.get('Sub_LEG_Count')
            status.leg_source = 'external'
            
            if status.interface_speed_max:
                try:
                    status.leg_capacity_mbps = float(status.interface_speed_max)
                    status.leg_util_pct = round((float(status.avg_max_mbitrate or 0) / float(status.interface_speed_max)) * 100, 1)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass


def refresh_external_utilization():
    global _last_external_error, _last_external_error_at

    engine = _get_external_engine()
    if engine is None:
        logger.info('External utilization database is not configured, skipping refresh')
        return

    try:
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

            status = LinkStatus.query.filter_by(link_id=link.id).first()
            if not status:
                status = LinkStatus(link_id=link.id)
                db.session.add(status)
                
            status.mw_util_pct = row.get('AVG_MAX_Util_RxTx_perc')
            status.mw_capacity_mbps = row.get('XPIC_MW_Link_Capacity') if row.get('XPIC_MW_Link_Capacity') is not None else row.get('MW_Link_Capacity')
            status.metric_source = 'external'
            status.last_metric_at = datetime.utcnow()

        # Refresh aggregated leg metadata files as snapshots for lookup and history.
        leg_names = db.session.query(Link.leg_name).filter(Link.leg_name.isnot(None)).distinct().all()
        for (leg_name,) in leg_names:
            if not leg_name:
                continue
            row = lookup_leg_info(leg_name)
            if not row:
                continue

            links = Link.query.filter_by(leg_name=row.get('LEG_Name')).all()
            for link in links:
                status = LinkStatus.query.filter_by(link_id=link.id).first()
                if not status:
                    status = LinkStatus(link_id=link.id)
                    db.session.add(status)
                status.avg_max_mbitrate = row.get('AVG_MAX_MBitRate')
                status.interface_speed_min = row.get('Interface_Speed_Min')
                status.interface_speed_max = row.get('Interface_Speed_Max')
                status.sub_leg_count = row.get('Sub_LEG_Count')
                status.leg_source = 'external'
                
                if status.interface_speed_max:
                    try:
                        status.leg_capacity_mbps = float(status.interface_speed_max)
                        status.leg_util_pct = round((float(status.avg_max_mbitrate or 0) / float(status.interface_speed_max)) * 100, 1)
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass

        db.session.commit()

        # Clear error state on success
        _last_external_error = None
        _last_external_error_at = None
        logger.info('External utilization refresh completed successfully')

    except Exception as exc:
        db.session.rollback()
        _last_external_error = str(exc)
        _last_external_error_at = datetime.utcnow()
        logger.error(f'Error refreshing external utilization: {exc}')
        logger.error(traceback.format_exc())
