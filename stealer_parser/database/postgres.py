"""PostgreSQL database exporter for stealer parser data."""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    from psycopg2 import DatabaseError as PostgreSQLError
    PSYCOPG2_AVAILABLE = True

except ImportError:
    psycopg2 = None
    DictCursor = None
    PostgreSQLError = Exception
    PSYCOPG2_AVAILABLE = False

from verboselogs import VerboseLogger

from ..models import Credential, Cookie, Leak, System, SystemData

logger = logging.getLogger(__name__)


def truncate_string(value: Optional[str], max_length: int) -> Optional[str]:
    """Safely truncate a string to fit database field limits.
    
    Parameters
    ----------
    value : str or None
        The string value to truncate.
    max_length : int
        Maximum allowed length.
    
    Returns
    -------
    str or None
        Truncated string or None if input was None.
    
    """
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length-3] + "..."


def safe_credential_data(cred: Credential, system_id: int) -> tuple:
    """Safely prepare credential data with field length limits.
    
    Parameters
    ----------
    cred : Credential
        The credential object.
    system_id : int
        The system ID.
    
    Returns
    -------
    tuple
        Safely truncated credential data tuple.
    
    """
    return (
        system_id,
        truncate_string(cred.software, 255),
        truncate_string(cred.host, 2000),  # TEXT field, but be reasonable
        truncate_string(cred.username, 1000),  # Increased limit
        truncate_string(cred.password, 2000),  # TEXT field, but be reasonable
        truncate_string(cred.domain, 255),
        truncate_string(cred.local_part, 255),
        truncate_string(cred.email_domain, 255),
        truncate_string(cred.filepath, 2000),  # TEXT field, but be reasonable
        truncate_string(cred.stealer_name, 50)
    )


def safe_cookie_data(cookie: Cookie, system_id: int) -> tuple:
    """Safely prepare cookie data with field length limits.
    
    Parameters
    ----------
    cookie : Cookie
        The cookie object.
    system_id : int
        The system ID.
    
    Returns
    -------
    tuple
        Safely truncated cookie data tuple.
    
    """
    return (
        system_id,
        truncate_string(cookie.domain, 255),
        truncate_string(cookie.domain_specified, 10),
        truncate_string(cookie.path, 2000),  # TEXT field, but be reasonable
        truncate_string(cookie.secure, 10),
        truncate_string(cookie.expiry, 50),
        truncate_string(cookie.name, 255),
        truncate_string(cookie.value, 2000),  # TEXT field, but be reasonable
        truncate_string(cookie.browser, 100),
        truncate_string(cookie.profile, 255),
        truncate_string(cookie.filepath, 2000),  # TEXT field, but be reasonable
        truncate_string(cookie.stealer_name, 50)
    )


class PostgreSQLExporter:
    """PostgreSQL database exporter for stealer parser data.
    
    This class handles connecting to PostgreSQL database, creating tables,
    and inserting parsed stealer data including credentials, system info, and cookies.
    
    Attributes
    ----------
    connection : psycopg2.connection
        The database connection object.
    logger : VerboseLogger
        The logger instance for debugging and error reporting.
    
    """
    
    def __init__(
        self,
        db_pool: Any,
        logger: Optional[VerboseLogger] = None,
    ) -> None:
        """Initialize PostgreSQL exporter.
        
        Parameters
        ----------
        db_pool : psycopg2.pool.SimpleConnectionPool
            A psycopg2 connection pool.
        logger : VerboseLogger, optional
            Logger instance for debugging.
        
        """
        self.logger = logger or VerboseLogger(__name__)
        self.db_pool = db_pool
        self.connection: Optional[Any] = None
        
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )
        
    
    def connect(self) -> None:
        """Get a connection from the pool."""
        try:
            self.connection = self.db_pool.getconn()
            self.logger.debug("Acquired connection from pool")
        except Exception as e:
            self.logger.error(f"Failed to get connection from pool: {e}")


    def disconnect(self) -> None:
        """Return a connection to the pool."""
        if self.connection:
            self.db_pool.putconn(self.connection)
            self.connection = None
            self.logger.debug("Returned connection to pool")
    
    def create_tables(self) -> None:
        """Create database tables if they don't exist.
        
        Reads schema from schema.sql file and executes the statements.
        
        Raises
        ------
        PostgreSQLError
            If table creation fails.
        FileNotFoundError
            If schema.sql file is not found.
        
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        try:
            schema_path = Path(__file__).parent / "schema.sql"
            schema_sql = schema_path.read_text()
            
            with self.connection.cursor() as cursor:  # type: ignore as cursor:
                cursor.execute(schema_sql)
                self.connection.commit()  # type: ignore
                
            self.logger.verbose("Database tables created successfully")
            
        except (Exception, FileNotFoundError) as err:
            self.logger.error(f"Failed to create database tables: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
    
    def insert_leak(self, leak: Leak) -> int:
        """Insert leak metadata and return the leak ID.
        
        Parameters
        ----------
        leak : Leak
            The leak object containing metadata.
        
        Returns
        -------
        int
            The database ID of the inserted leak.
        
        Raises
        ------
        PostgreSQLError
            If insertion fails.
        
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        try:
            with self.connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO leaks (filename, systems_count)
                    VALUES (%(filename)s, %(systems_count)s)
                    RETURNING id
                    """,
                    {
                        "filename": leak.filename,
                        "systems_count": len(leak.systems_data)
                    }
                )
                
                leak_id = cursor.fetchone()["id"]
                self.logger.debug(f"Inserted leak with ID: {leak_id}")
                return leak_id
                
        except PostgreSQLError as err:
            self.logger.error(f"Failed to insert leak: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
    
    def insert_system(self, system: System, leak_id: int) -> int:
        """Insert system information and return the system ID.
        
        Parameters
        ----------
        system : System
            The system object with machine information.
        leak_id : int
            The leak ID this system belongs to.
        
        Returns
        -------
        int
            The database ID of the inserted system.
        
        Raises
        ------
        PostgreSQLError
            If insertion fails.
        
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        try:
            with self.connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO systems (
                        leak_id, machine_id, computer_name, hardware_id,
                        machine_user, ip_address, country, log_date
                    )
                    VALUES (
                        %(leak_id)s, %(machine_id)s, %(computer_name)s, %(hardware_id)s,
                        %(machine_user)s, %(ip_address)s, %(country)s, %(log_date)s
                    )
                    RETURNING id
                    """,
                    {
                        "leak_id": leak_id,
                        "machine_id": truncate_string(system.machine_id, 255),
                        "computer_name": truncate_string(system.computer_name, 255),
                        "hardware_id": truncate_string(system.hardware_id, 255),
                        "machine_user": truncate_string(system.machine_user, 255),
                        "ip_address": system.ip_address,  # INET type, should be valid
                        "country": truncate_string(system.country, 10),
                        "log_date": truncate_string(system.log_date, 255)
                    }
                )
                
                system_id = cursor.fetchone()["id"]
                self.logger.debug(f"Inserted system with ID: {system_id}")
                return system_id
                
        except PostgreSQLError as err:
            self.logger.error(f"Failed to insert system: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
    
    def insert_credentials(self, credentials: list[Credential], system_id: int) -> int:
        """Insert credentials for a system with robust error handling.
        
        Parameters
        ----------
        credentials : list[Credential]
            List of credential objects to insert.
        system_id : int
            The system ID these credentials belong to.
        
        Returns
        -------
        int
            Number of credentials successfully inserted.
        
        Raises
        ------
        PostgreSQLError
            If critical insertion failure occurs.
        
        """
        if not self.connection or not credentials:
            return 0
        
        inserted_count = 0
        
        try:
            with self.connection.cursor() as cursor:  # type: ignore
                # First, try batch insert with safe data
                credential_data = []
                for cred in credentials:
                    credential_data.append(safe_credential_data(cred, system_id))
                
                try:
                    cursor.executemany(
                        """
                        INSERT INTO credentials (
                            system_id, software, host, username, password,
                            domain, local_part, email_domain, filepath, stealer_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        credential_data
                    )
                    
                    inserted_count = cursor.rowcount
                    self.logger.debug(f"Batch inserted {inserted_count} credentials for system {system_id}")
                    return inserted_count
                    
                except PostgreSQLError as batch_err:
                    self.logger.warning(f"Batch insert failed, falling back to individual inserts: {batch_err}")
                    
                    # Rollback the failed batch transaction
                    if self.connection:
                        self.connection.rollback()  # type: ignore
                    
                    # Fall back to individual inserts
                    for i, cred in enumerate(credentials):
                        try:
                            safe_data = safe_credential_data(cred, system_id)
                            cursor.execute(
                                """
                                INSERT INTO credentials (
                                    system_id, software, host, username, password,
                                    domain, local_part, email_domain, filepath, stealer_name
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                safe_data
                            )
                            inserted_count += 1
                            
                        except PostgreSQLError as individual_err:
                            self.logger.warning(
                                f"Failed to insert credential {i+1}/{len(credentials)} "
                                f"(username: {truncate_string(cred.username, 50)}): {individual_err}"
                            )
                            # Continue with next credential
                            continue
                    
                    self.logger.info(f"Individual inserts completed: {inserted_count}/{len(credentials)} credentials inserted")
                    return inserted_count
                
        except PostgreSQLError as err:
            self.logger.error(f"Critical failure inserting credentials: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
    
    def insert_cookies(self, cookies: list[Cookie], system_id: int) -> int:
        """Insert cookies for a system with robust error handling.
        
        Parameters
        ----------
        cookies : list[Cookie]
            List of cookie objects to insert.
        system_id : int
            The system ID these cookies belong to.
        
        Returns
        -------
        int
            Number of cookies successfully inserted.
        
        Raises
        ------
        PostgreSQLError
            If critical insertion failure occurs.
        
        """
        if not self.connection or not cookies:
            return 0
        
        inserted_count = 0
        
        try:
            with self.connection.cursor() as cursor:  # type: ignore
                # First, try batch insert with safe data
                cookie_data = []
                for cookie in cookies:
                    cookie_data.append(safe_cookie_data(cookie, system_id))
                
                try:
                    cursor.executemany(
                        """
                        INSERT INTO cookies (
                            system_id, domain, domain_specified, path, secure,
                            expiry, name, value, browser, profile, filepath, stealer_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        cookie_data
                    )
                    
                    inserted_count = cursor.rowcount
                    self.logger.debug(f"Batch inserted {inserted_count} cookies for system {system_id}")
                    return inserted_count
                    
                except PostgreSQLError as batch_err:
                    self.logger.warning(f"Batch insert failed, falling back to individual inserts: {batch_err}")
                    
                    # Rollback the failed batch transaction
                    if self.connection:
                        self.connection.rollback()  # type: ignore
                    
                    # Fall back to individual inserts
                    for i, cookie in enumerate(cookies):
                        try:
                            safe_data = safe_cookie_data(cookie, system_id)
                            cursor.execute(
                                """
                                INSERT INTO cookies (
                                    system_id, domain, domain_specified, path, secure,
                                    expiry, name, value, browser, profile, filepath, stealer_name
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                safe_data
                            )
                            inserted_count += 1
                            
                        except PostgreSQLError as individual_err:
                            self.logger.warning(
                                f"Failed to insert cookie {i+1}/{len(cookies)} "
                                f"(domain: {truncate_string(cookie.domain, 50)}): {individual_err}"
                            )
                            # Continue with next cookie
                            continue
                    
                    self.logger.info(f"Individual inserts completed: {inserted_count}/{len(cookies)} cookies inserted")
                    return inserted_count
                
        except PostgreSQLError as err:
            self.logger.error(f"Critical failure inserting cookies: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
    
    def export_leak(self, leak: Leak) -> Dict[str, int]:
        """Export complete leak data to PostgreSQL database.
        
        Parameters
        ----------
        leak : Leak
            The leak object containing all parsed data.
        
        Returns
        -------
        Dict[str, int]
            Statistics of exported data including counts of systems, credentials, and cookies.
        
        Raises
        ------
        PostgreSQLError
            If export operation fails.
        
        """
        if not self.connection:
            self.connect()
        
        stats = {
            "systems": 0,
            "credentials": 0,
            "cookies": 0
        }
        
        try:
            # Start transaction
            self.connection.autocommit  # type: ignore = False
            
            # Insert leak metadata
            leak_id = self.insert_leak(leak)
            
            # Process each system with individual error handling
            for i, system_data in enumerate(leak.systems_data):
                try:
                    # Insert system if it has valid system info
                    if system_data.system:
                        system_id = self.insert_system(system_data.system, leak_id)
                        stats["systems"] += 1
                    else:
                        # Create a placeholder system record if we only have credentials/cookies
                        placeholder_system = System()
                        system_id = self.insert_system(placeholder_system, leak_id)
                        stats["systems"] += 1
                    
                    # Insert credentials with error handling
                    if system_data.credentials:
                        try:
                            cred_count = self.insert_credentials(system_data.credentials, system_id)
                            stats["credentials"] += cred_count
                        except Exception as cred_err:
                            self.logger.warning(f"Failed to insert some credentials for system {i+1}: {cred_err}")
                    
                    # Insert cookies with error handling  
                    if system_data.cookies:
                        try:
                            cookie_count = self.insert_cookies(system_data.cookies, system_id)
                            stats["cookies"] += cookie_count
                        except Exception as cookie_err:
                            self.logger.warning(f"Failed to insert some cookies for system {i+1}: {cookie_err}")
                            
                except Exception as system_err:
                    self.logger.error(f"Failed to process system {i+1}/{len(leak.systems_data)}: {system_err}")
                    # Continue processing other systems
                    continue
            
            # Commit transaction
            self.connection.commit()  # type: ignore
            
            self.logger.info(
                f"Successfully exported leak to database: "
                f"{stats['systems']} systems, {stats['credentials']} credentials, "
                f"{stats['cookies']} cookies"
            )
            
            return stats
            
        except PostgreSQLError as err:
            self.logger.error(f"Failed to export leak to database: {err}")
            if self.connection:
                self.connection.rollback()  # type: ignore
            raise
        
        finally:
            self.connection.autocommit  # type: ignore = True
    
    def test_connection(self) -> bool:
        """Test database connection and return success status.
        
        Returns
        -------
        bool
            True if connection successful, False otherwise.
        
        """
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:  # type: ignore as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            self.logger.debug("Database connection test successful")
            return result is not None
            
        except PostgreSQLError as err:
            self.logger.error(f"Database connection test failed: {err}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        if not self.connection:
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type:
            if self.connection:
                self.connection.rollback()  # type: ignore
                self.logger.error("Transaction rolled back due to error")
        self.disconnect()