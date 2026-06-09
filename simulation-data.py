#!/usr/bin/env python3
"""
Test data generator for MW Backup Link Monitor System.
Creates sample links with IPs from 172.50.0.2 to 172.50.0.11.
"""

from app import create_app
from app.extensions import db
from app.models import Link, LinkStatus
import random
from datetime import datetime, timezone

def create_test_links():
    """Create test links with IPs from 172.50.0.2 to 172.50.0.11"""

    # Sample data for variety
    legs = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL']
    cities = ['City Center', 'North Suburb', 'South Suburb', 'East District', 'West District', 'Industrial Park', 'Business Bay']

    app = create_app()

    with app.app_context():
        print("Creating test links...")

        # Clear existing test data (optional - comment out if you want to keep existing data)
        # Link.query.filter(Link.link_id.like('TEST%')).delete()
        # db.session.commit()

        created_count = 0

        for i in range(3, 13):  # 172.20.0.3 to 172.20.0.12
            link_id = f"TEST_LINK_{i:02d}"
            leg_name = legs[(i-2) % len(legs)]
            site_a = f"{cities[(i-1) % len(cities)]} Tower"
            site_b = f"{cities[i % len(cities)]} Node"
            link_type = 'microwave' if i % 2 == 0 else 'fiber'

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
                mw_ip=f"172.20.0.{i}",
                link_type=link_type,
                notes=f"Simulated backup link {i} for demonstration purposes. Connecting {site_a} to {site_b}.",
                is_active=True
            )

            db.session.add(link)
            db.session.flush()  # Get the ID

            # Create initial status record
            status = LinkStatus(
                link_id=link.id,
                mw_status='up',
                last_ping_at=datetime.utcnow(),
                consecutive_timeouts=0,
                leg_util_pct=round(random.uniform(10.0, 95.0), 2),
                leg_capacity_mbps=round(random.uniform(100.0, 1000.0), 2),
                mw_util_pct=round(random.uniform(10.0, 85.0), 2),
                mw_capacity_mbps=round(random.uniform(100.0, 500.0), 2),
                avg_max_mbitrate=round(random.uniform(50.0, 800.0), 2),
                interface_speed_min=100,
                interface_speed_max=1000,
                sub_leg_count=random.randint(1, 4),
                metric_source='simulation',
                leg_source='simulation'
            )
            db.session.add(status)

            created_count += 1
            print(f"Created link: {link_id} (172.20.0.{i}) - {leg_name}")

        db.session.commit()
        print(f"\nSuccessfully created {created_count} test links!")
        print("IP range: 172.20.0.3 - 172.20.0.12")

if __name__ == '__main__':
    create_test_links()