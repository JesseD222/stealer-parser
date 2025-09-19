#!/usr/bin/env python3
"""Test script for PostgreSQL database export functionality."""

import sys
from pathlib import Path

# Add the stealer_parser to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stealer_parser.database.postgres import PostgreSQLExporter, PSYCOPG2_AVAILABLE
from stealer_parser.models import Credential, Cookie, Leak, System, SystemData
from stealer_parser.helpers import init_logger


def create_test_data() -> Leak:
    """Create sample test data for testing database export."""
    
    # Create a test leak
    leak = Leak(filename="test_archive.rar")
    
    # Create test system data
    system = System(
        machine_id="TEST123",
        computer_name="TEST-PC",
        hardware_id="HWID-123456",
        machine_user="testuser",
        ip_address="192.168.1.100",
        country="US",
        log_date="2024-01-15"
    )
    
    # Create test credentials
    credentials = [
        Credential(
            software="Chrome",
            host="https://example.com",
            username="user@example.com",
            password="password123",
            domain="example.com",
            local_part="user",
            email_domain="example.com",
            filepath="/Chrome/passwords.txt",
            stealer_name="redline"
        ),
        Credential(
            software="Firefox",
            host="https://bank.com",
            username="account123",
            password="secret456",
            domain="bank.com",
            filepath="/Firefox/logins.txt",
            stealer_name="redline"
        )
    ]
    
    # Create test cookies
    cookies = [
        Cookie(
            domain="example.com",
            domain_specified="TRUE",
            path="/",
            secure="FALSE",
            expiry="1735689600",
            name="session_id",
            value="abc123def456",
            browser="Chrome",
            profile="Default",
            filepath="/Chrome/cookies.txt",
            stealer_name="redline"
        )
    ]
    
    # Create system data
    system_data = SystemData(
        system=system,
        credentials=credentials,
        cookies=cookies
    )
    
    leak.systems_data.append(system_data)
    
    return leak


def test_database_export():
    """Test the database export functionality."""
    
    print("Testing PostgreSQL Database Export Component")
    print("=" * 50)
    
    # Check if psycopg2 is available
    if not PSYCOPG2_AVAILABLE:
        print("❌ PSYCOPG2 NOT AVAILABLE")
        print("Install with: pip install psycopg2-binary")
        return False
    
    print("✅ psycopg2 is available")
    
    # Initialize logger
    logger = init_logger("TestLogger", 2)  # Debug level
    
    # Create test data
    print("📊 Creating test data...")
    leak = create_test_data()
    print(f"   - Systems: {len(leak.systems_data)}")
    print(f"   - Credentials: {sum(len(sd.credentials) for sd in leak.systems_data)}")
    print(f"   - Cookies: {sum(len(sd.cookies) for sd in leak.systems_data)}")
    
    # Test database connection (using default test database parameters)
    print("\\n🔌 Testing database connection...")
    
    try:
        db_exporter = PostgreSQLExporter(
            logger=logger,
            host="localhost",
            port=5432,
            database="stealer_parser_test",  # Using test database
            user="postgres",
            password=""  # Adjust as needed
        )
        
        print("   - PostgreSQL exporter created")
        
        # Test connection
        with db_exporter:
            if db_exporter.test_connection():
                print("✅ Database connection successful")
                
                print("\\n🏗️  Creating database tables...")
                db_exporter.create_tables()
                print("✅ Tables created successfully")
                
                print("\\n📤 Exporting test data...")
                stats = db_exporter.export_leak(leak)
                
                print("✅ Export completed successfully!")
                print(f"   - Systems exported: {stats['systems']}")
                print(f"   - Credentials exported: {stats['credentials']}")
                print(f"   - Cookies exported: {stats['cookies']}")
                
                return True
                
            else:
                print("❌ Database connection failed")
                return False
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.debug("Full error details:", exc_info=True)
        return False


if __name__ == "__main__":
    print("Stealer Parser - PostgreSQL Database Export Test")
    print("Note: This test requires a PostgreSQL server running locally")
    print("with a database named 'stealer_parser_test'\\n")
    
    success = test_database_export()
    
    if success:
        print("\\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\\n💥 Some tests failed!")
        sys.exit(1)