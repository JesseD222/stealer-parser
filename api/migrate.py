#!/usr/bin/env python3
"""
Database migration and management script.
Creates tables and handles schema updates.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api.database import db_manager, Base
from stealer_parser.helpers import init_logger
from sqlalchemy.sql import text


async def create_tables():
    """Create all database tables."""
    logger = init_logger("DatabaseMigration", 2)
    
    try:
        logger.info("Initializing database connection...")
        await db_manager.init_database()
        
        logger.info("Creating database tables...")
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
        # Create indexes for performance
        await create_performance_indexes()
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
    finally:
        await db_manager.close()


async def create_performance_indexes():
    """Create additional performance indexes."""
    logger = init_logger("DatabaseIndexes", 2)
    
    # Additional indexes for high-performance queries
    indexes = [
        # Composite indexes for common query patterns
        "CREATE INDEX IF NOT EXISTS idx_creds_domain_stealer_risk ON extracted_credentials(domain, stealer_name, risk_level)",
        "CREATE INDEX IF NOT EXISTS idx_cookies_domain_browser_secure ON extracted_cookies(domain, browser, secure)",
        "CREATE INDEX IF NOT EXISTS idx_systems_country_stealer ON compromised_systems(country, stealer_name)",
        
        # Time-based indexes for analytics
        "CREATE INDEX IF NOT EXISTS idx_sessions_upload_status ON parse_sessions(upload_time, status)",
        "CREATE INDEX IF NOT EXISTS idx_creds_created_risk ON extracted_credentials(created_at, risk_level)",
        
        # Full-text search preparation (PostgreSQL specific)
        # These will be ignored by SQLite
        "CREATE INDEX IF NOT EXISTS idx_creds_username_gin ON extracted_credentials USING gin(to_tsvector('english', username))",
        "CREATE INDEX IF NOT EXISTS idx_creds_domain_gin ON extracted_credentials USING gin(to_tsvector('english', domain))",
    ]
    
    async with db_manager.get_session() as session:
        for index_sql in indexes:
            try:
                await session.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'custom'}")
            except Exception as e:
                # Ignore errors for PostgreSQL-specific indexes when using SQLite
                if "gin" not in index_sql.lower():
                    logger.warning(f"Failed to create index: {e}")


async def drop_tables():
    """Drop all database tables (USE WITH CAUTION)."""
    logger = init_logger("DatabaseDrop", 2)
    
    confirmation = input("Are you sure you want to DROP ALL TABLES? This will delete all data! (type 'DELETE' to confirm): ")
    
    if confirmation != "DELETE":
        logger.info("Operation cancelled")
        return
    
    try:
        await db_manager.init_database()
        
        logger.warning("DROPPING ALL TABLES...")
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("All tables dropped")
        
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise
    finally:
        await db_manager.close()


async def show_stats():
    """Show database statistics."""
    logger = init_logger("DatabaseStats", 2)
    
    try:
        await db_manager.init_database()
        
        async with db_manager.get_session() as session:
            # Get table counts
            tables = [
                ("parse_sessions", "Parse Sessions"),
                ("compromised_systems", "Compromised Systems"), 
                ("extracted_credentials", "Extracted Credentials"),
                ("extracted_cookies", "Extracted Cookies"),
            ]
            
            print("\n=== Database Statistics ===")
            
            total_records = 0
            for table_name, display_name in tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    print(f"{display_name}: {count:,}")
                    total_records += count
                except Exception as e:
                    print(f"{display_name}: Error - {e}")
            
            print(f"\nTotal Records: {total_records:,}")
            
            # Get recent activity
            try:
                result = await session.execute(text("""
                    SELECT status, COUNT(*) as count 
                    FROM parse_sessions 
                    GROUP BY status 
                    ORDER BY count DESC
                """))
                
                print("\n=== Session Status Distribution ===")
                for row in result:
                    print(f"{row.status}: {row.count}")
                    
            except Exception as e:
                print(f"Failed to get session stats: {e}")
            
            # Get top domains
            try:
                result = await session.execute(text("""
                    SELECT domain, COUNT(*) as count 
                    FROM extracted_credentials 
                    WHERE domain IS NOT NULL
                    GROUP BY domain 
                    ORDER BY count DESC 
                    LIMIT 10
                """))
                
                print("\n=== Top 10 Compromised Domains ===")
                for row in result:
                    print(f"{row.domain}: {row.count} credentials")
                    
            except Exception as e:
                print(f"Failed to get domain stats: {e}")
    
    except Exception as e:
        logger.error(f"Failed to show stats: {e}")
        raise
    finally:
        await db_manager.close()


async def main():
    """Main entry point for database management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stealer Parser Database Management")
    parser.add_argument(
        "action", 
        choices=["create", "drop", "stats", "migrate"],
        help="Database action to perform"
    )
    
    args = parser.parse_args()
    
    if args.action == "create" or args.action == "migrate":
        await create_tables()
        print("Database tables created successfully")
    
    elif args.action == "drop":
        await drop_tables()
    
    elif args.action == "stats":
        await show_stats()


if __name__ == "__main__":
    asyncio.run(main())