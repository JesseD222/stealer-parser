"""PostgreSQL database exporter for stealer parser data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from verboselogs import VerboseLogger

from .dao.base import CookiesDAO, CredentialsDAO, LeaksDAO, SystemsDAO
from .dao.vault import VaultDAO
from .dao.user_file import UserFilesDAO

if TYPE_CHECKING:
    from stealer_parser.models.leak import Leak

try:
    import psycopg2
    import psycopg2.pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class PostgreSQLExporter:
    """Orchestrates exporting stealer data to a PostgreSQL database using DAOs."""

    def __init__(
        self,
        db_pool: Any,
        leaks_dao: LeaksDAO,
        systems_dao: SystemsDAO,
        credentials_dao: CredentialsDAO,
        cookies_dao: CookiesDAO,
        vaults_dao: VaultDAO,
        user_files_dao: UserFilesDAO,
        logger: Optional[VerboseLogger] = None,
    ) -> None:
        """Initialize PostgreSQL exporter.

        Parameters
        ----------
        db_pool : psycopg2.pool.SimpleConnectionPool
            A psycopg2 connection pool.
        leaks_dao : LeaksDAO
            Data access object for leaks.
        systems_dao : SystemsDAO
            Data access object for systems.
        credentials_dao : CredentialsDAO
            Data access object for credentials.
        cookies_dao : CookiesDAO
            Data access object for cookies.
        logger : VerboseLogger, optional
            Logger instance for debugging.

        """
        self.logger = logger or VerboseLogger(__name__)
        self.db_pool = db_pool

        # Initialize DAOs
        self.leaks_dao = leaks_dao
        self.systems_dao = systems_dao
        self.credentials_dao = credentials_dao
        self.cookies_dao = cookies_dao
        self.vaults_dao = vaults_dao
        self.user_files_dao = user_files_dao

        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def test_connection(self) -> bool:
        """Test the database connection.

        Returns
        -------
        bool
            True if connection is successful, False otherwise.
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            self.logger.info("Database connection successful")
            return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def recreate_schema(self) -> None:
        """Drop and recreate the database schema."""
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                schema_path = Path(__file__).parent / "schema.sql"
                schema_sql = schema_path.read_text()
                cursor.execute(schema_sql)
                conn.commit()
            self.logger.info("Database schema recreated successfully")
        except Exception as e:
            self.logger.error(f"Failed to recreate schema: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def export_leak(self, leak: Leak) -> Dict[str, int]:
        """Export a full leak to the database.

        Parameters
        ----------
        leak : Leak
            The leak object to export.

        Returns
        -------
        Dict[str, int]
            Statistics of exported data.
        """
        stats = {"systems": 0, "credentials": 0, "cookies": 0, "vaults": 0, "user_files": 0}

        conn = None
        try:
            conn = self.db_pool.getconn()
            conn.autocommit = False

            leak_id = self.leaks_dao.insert(leak, conn=conn)

            for system_data in leak.systems:
                system_id = self.systems_dao.insert(system_data.system, leak_id, conn=conn)
                stats["systems"] += 1

                if system_data.credentials:
                    stats["credentials"] += self.credentials_dao.bulk_insert(system_data.credentials, system_id, conn=conn)

                if system_data.cookies:
                    stats["cookies"] += self.cookies_dao.bulk_insert(system_data.cookies, system_id, conn=conn)

                if getattr(system_data, "vaults", None):
                    stats["vaults"] += self.vaults_dao.bulk_insert(system_data.vaults, system_id, conn=conn)

                if getattr(system_data, "user_files", None):
                    stats["user_files"] += self.user_files_dao.bulk_insert(system_data.user_files, system_id, conn=conn)

            self.leaks_dao.update_counts(leak_id, stats["systems"], conn=conn)
            conn.commit()

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self.logger.error(f"Error during database export: {e}")
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)

        return stats