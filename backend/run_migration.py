#!/usr/bin/env python3
"""
Simple migration runner for Project 2501 database migrations.
Applies SQL migration files in order.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List

# Add the app directory to Python path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.connection import get_db_manager
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_migration_files(migration_dir: Path) -> List[Path]:
    """Get all migration files sorted by name."""
    if not migration_dir.exists():
        logger.error(f"Migration directory not found: {migration_dir}")
        return []
    
    migration_files = []
    for file_path in migration_dir.glob("*.sql"):
        if file_path.is_file():
            migration_files.append(file_path)
    
    # Sort by filename (assuming numbered prefixes like 001_, 002_, etc.)
    migration_files.sort(key=lambda x: x.name)
    return migration_files


def create_migration_tracking_table(db_manager):
    """Create table to track applied migrations."""
    try:
        with db_manager.engine.connect() as connection:
            # Create migrations tracking table if it doesn't exist
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS applied_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            connection.execute(text(create_table_sql))
            connection.commit()
            logger.info("Migration tracking table ready")
    except Exception as e:
        logger.error(f"Failed to create migration tracking table: {e}")
        raise


def is_migration_applied(db_manager, filename: str) -> bool:
    """Check if a migration has already been applied."""
    try:
        with db_manager.engine.connect() as connection:
            result = connection.execute(
                text("SELECT COUNT(*) FROM applied_migrations WHERE filename = :filename"),
                {"filename": filename}
            )
            count = result.scalar()
            return count > 0
    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return False


def apply_migration(db_manager, migration_file: Path) -> bool:
    """Apply a single migration file."""
    filename = migration_file.name
    
    if is_migration_applied(db_manager, filename):
        logger.info(f"Skipping {filename} (already applied)")
        return True
    
    logger.info(f"Applying migration: {filename}")
    
    try:
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Apply migration in a transaction
        with db_manager.engine.begin() as connection:
            # Execute the migration SQL
            connection.execute(text(migration_sql))
            
            # Record that this migration was applied
            connection.execute(
                text("INSERT INTO applied_migrations (filename) VALUES (:filename)"),
                {"filename": filename}
            )
            
        logger.info(f"Successfully applied migration: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply migration {filename}: {e}")
        return False


def run_migrations(migration_dir: str = None) -> bool:
    """Run all pending migrations."""
    if migration_dir is None:
        # Default to migrations directory relative to this script
        script_dir = Path(__file__).parent
        migration_dir = script_dir / "app" / "database" / "migrations"
    else:
        migration_dir = Path(migration_dir)
    
    logger.info(f"Running migrations from: {migration_dir}")
    
    # Initialize database manager
    db_manager = get_db_manager()
    db_manager.initialize()
    
    try:
        # Create migration tracking table
        create_migration_tracking_table(db_manager)
        
        # Get migration files
        migration_files = get_migration_files(migration_dir)
        
        if not migration_files:
            logger.info("No migration files found")
            return True
        
        logger.info(f"Found {len(migration_files)} migration files")
        
        # Apply each migration
        success_count = 0
        for migration_file in migration_files:
            if apply_migration(db_manager, migration_file):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping at: {migration_file.name}")
                return False
        
        logger.info(f"Successfully applied {success_count} migrations")
        return True
        
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        return False
    
    finally:
        db_manager.close()


if __name__ == "__main__":
    """Run migrations when script is executed directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument(
        "--migration-dir", 
        help="Directory containing migration files",
        default=None
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be migrated without applying"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        # Show pending migrations without applying
        migration_dir = Path(args.migration_dir) if args.migration_dir else Path(__file__).parent / "app" / "database" / "migrations"
        migration_files = get_migration_files(migration_dir)
        
        print(f"Found {len(migration_files)} migration files:")
        for migration_file in migration_files:
            print(f"  - {migration_file.name}")
    else:
        # Run migrations
        success = run_migrations(args.migration_dir)
        exit_code = 0 if success else 1
        sys.exit(exit_code)