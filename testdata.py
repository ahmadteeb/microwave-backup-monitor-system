#!/usr/bin/env python3
"""
Test data generator for MW Backup Link Monitor System.
Creates sample links with IPs from 172.50.0.2 to 172.50.0.11.
"""

from app import create_app
from app.extensions import db
from app.models import Link, LinkStatus
from datetime import datetime, timezone

def create_test_links():
    """Create test links with IPs from 172.50.0.2 to 172.50.0.11"""

    # Sample data for variety
    legs = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL']
    sites_a = ['ALPHA_BASE', 'BETA_STATION', 'GAMMA_HUB', 'DELTA_REPEATER', 'EPSILON_NODE']
    sites_b = ['ZETA_ENDPOINT', 'ETA_TERMINAL', 'THETA_GATEWAY', 'IOTA_SWITCH', 'KAPPA_ROUTER']
    equipment_types = ['MW_Radio_Pro', 'Fiber_Optic_Transceiver', 'Satellite_Dish', 'Wireless_Bridge', 'Network_Switch']

    app = create_app()

    with app.app_context():
        print("Creating test links...")

        # Clear existing test data (optional - comment out if you want to keep existing data)
        # Link.query.filter(Link.link_id.like('TEST%')).delete()
        # db.session.commit()

        created_count = 0

        for i in range(2, 12):  # 172.50.0.2 to 172.50.0.11
            ip = f"172.50.0.{i}"
            link_id = f"TEST_LINK_{i:02d}"
            leg_name = legs[(i-2) % len(legs)]
            site_a = sites_a[(i-2) % len(sites_a)]
            site_b = sites_b[(i-2) % len(sites_b)]
            equipment_a = equipment_types[(i-2) % len(equipment_types)]
            equipment_b = equipment_types[(i-1) % len(equipment_types)]

            # Check if link already exists
            existing = Link.query.filter_by(link_id=link_id).first()
            if existing:
                print(f"Link {link_id} already exists, skipping...")
                continue

            # Create new link
            link = Link(
                link_id=link_id,
                leg_name=leg_name,
                site_a=site_a,
                site_b=site_b,
                mw_ip=ip,
                equipment_a=equipment_a,
                equipment_b=equipment_b,
                link_type='microwave',
                notes=f'Test link {i} created on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}',
                is_active=True
            )

            db.session.add(link)
            db.session.flush()  # Get the ID

            # Create initial status record
            status = LinkStatus(
                link_id=link.id,
                mw_status='unknown',
                last_ping_at=None,
                consecutive_timeouts=0
            )
            db.session.add(status)

            created_count += 1
            print(f"Created link: {link_id} ({ip}) - {leg_name}")

        db.session.commit()
        print(f"\nSuccessfully created {created_count} test links!")
        print("IP range: 172.50.0.2 - 172.50.0.11")

if __name__ == '__main__':
    create_test_links()