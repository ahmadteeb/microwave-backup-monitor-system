"""
Database Migration CLI Script
Usage:
    python migrate.py

Runs database schema inspection and automatically creates missing tables,
missing columns, and missing indexes for SQLite, MySQL, and PostgreSQL in production.
"""
import sys
import logging
from app import create_app
from app.extensions import db
from app.services.migration_service import run_auto_migrations

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('migrate_cli')

def main():
    logger.info("Initializing Flask app for database migration...")
    app = create_app()
    with app.app_context():
        try:
            changes = run_auto_migrations(db, app=app)
            logger.info(f"Migration completed successfully. {len(changes)} schema changes applied.")
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            sys.exit(1)

if __name__ == '__main__':
    main()
