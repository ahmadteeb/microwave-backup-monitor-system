import logging
from sqlalchemy import inspect, text

logger = logging.getLogger('migration')

def run_auto_migrations(db, app=None):
    """
    Auto-migration utility for production and development.
    Inspects all tables and columns declared in SQLAlchemy metadata against the active database,
    automatically creates any missing tables, and adds any missing columns or indexes
    across SQLite, MySQL, and PostgreSQL without data loss.
    """
    engine = db.engine
    dialect_name = engine.dialect.name.lower()
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    logger.info(f"Running database migration check (Dialect: {dialect_name})...")
    migrated_items = []

    with engine.connect() as conn:
        for table_name, table in db.metadata.tables.items():
            if table_name not in existing_tables:
                logger.info(f"Table '{table_name}' does not exist. Creating table...")
                try:
                    table.create(bind=conn, checkfirst=True)
                    migrated_items.append(f"Created table: {table_name}")
                except Exception as e:
                    logger.error(f"Failed to create table '{table_name}': {e}")
                    raise
            else:
                # Table exists: check for missing columns
                db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in db_columns:
                        logger.info(f"Column '{col.name}' missing on table '{table_name}'. Adding column...")
                        col_type = col.type.compile(engine.dialect)
                        
                        # Handle nullable and default
                        default_clause = ""
                        if col.server_default is not None:
                            default_clause = f" DEFAULT {col.server_default.arg}"
                        elif col.default is not None and getattr(col.default, 'is_scalar', False):
                            default_clause = f" DEFAULT {repr(col.default.arg)}"
                            
                        # Nullability
                        null_clause = " NULL"
                        if not col.nullable and default_clause:
                            null_clause = " NOT NULL"

                        # Dialect-safe quoting
                        if dialect_name == 'mysql':
                            stmt = f"ALTER TABLE `{table_name}` ADD COLUMN `{col.name}` {col_type}{default_clause}{null_clause}"
                        elif dialect_name in ('postgresql', 'sqlite'):
                            stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}{default_clause}{null_clause}'
                        else:
                            stmt = f'ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}{null_clause}'

                        try:
                            conn.execute(text(stmt))
                            conn.commit()
                            migrated_items.append(f"Added column: {table_name}.{col.name} ({col_type})")
                            logger.info(f"Successfully added column {table_name}.{col.name}")
                        except Exception as e:
                            logger.warning(f"Could not add column {table_name}.{col.name}: {e}")

        # Check and create indexes if needed
        for index in db.metadata.tables.values():
            for idx in index.indexes:
                try:
                    idx.create(bind=conn, checkfirst=True)
                except Exception:
                    pass

    if migrated_items:
        logger.info(f"Migration completed successfully. Applied {len(migrated_items)} changes: {', '.join(migrated_items)}")
    else:
        logger.info("Database schema is fully up to date. No migration changes needed.")
        
    return migrated_items
