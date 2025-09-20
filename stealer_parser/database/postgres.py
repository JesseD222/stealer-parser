"""PostgreSQL database exporter for stealer parser data."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
import time
import random

from verboselogs import VerboseLogger
from stealer_parser.config import Settings

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
        settings: Optional[Settings] = None,
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
        self.settings = settings

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

        # Define retriable exceptions set
        retriable: Tuple[type[BaseException], ...]
        if PSYCOPG2_AVAILABLE:
            retriable = (
                psycopg2.OperationalError,  # connection issues, network blips
                psycopg2.InterfaceError,    # connection dropped
            )
        else:  # pragma: no cover - defensive
            retriable = (Exception,)
        self._retriable_exceptions = retriable

    def _conn_info_safe(self) -> str:
        if not self.settings:
            return "host=<?> port=<?> dbname=<?> user=<?>"
        return (
            f"host={getattr(self.settings, 'db_host', '?')} "
            f"port={getattr(self.settings, 'db_port', '?')} "
            f"dbname={getattr(self.settings, 'db_name', '?')} "
            f"user={getattr(self.settings, 'db_user', '?')}"
        )

    def _with_retry(self, op_name: str, func, *args, max_attempts: int = 3, base_delay: float = 0.5, **kwargs):
        attempt = 0
        last_exc: Exception | None = None
        while attempt < max_attempts:
            try:
                return func(*args, **kwargs)
            except self._retriable_exceptions as e:  # type: ignore[misc]
                last_exc = e
                attempt += 1
                if attempt >= max_attempts:
                    break
                delay = base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, delay * 0.25)
                sleep_for = delay + jitter
                self.logger.warning(
                    f"db_retry op={op_name} attempt={attempt}/{max_attempts} sleep={sleep_for:.2f}s info={self._conn_info_safe()} err={e}"
                )
                time.sleep(sleep_for)
            except Exception:
                # Non-retriable
                raise
        assert last_exc is not None
        raise last_exc

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
            conn = self._with_retry("test_connection:getconn", self.db_pool.getconn)
            self.logger.info(f"Database connection successful ({self._conn_info_safe()})")
            return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e} ({self._conn_info_safe()})")
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

        attempts = 0
        while True:
            conn = None
            try:
                attempts += 1
                conn = self._with_retry("export:getconn", self.db_pool.getconn)
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
                break

            except self._retriable_exceptions as e:  # type: ignore[misc]
                # Rollback and retry on transient DB errors
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                self.logger.warning(
                    f"db_retry op=export_leak attempt={attempts} err={e} leak={getattr(leak, 'filename', '?')} info={self._conn_info_safe()}"
                )
                if attempts >= 3:
                    self.logger.error(
                        f"Error during database export after retries: {e} (leak={getattr(leak, 'filename', '?')}, {self._conn_info_safe()})"
                    )
                    raise
                # small delay with backoff
                time.sleep(min(2 ** (attempts - 1) * 0.5, 3.0))

            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                self.logger.error(
                    f"Error during database export: {e} (leak={getattr(leak, 'filename', '?')}, {self._conn_info_safe()})"
                )
                raise
            finally:
                if conn:
                    self.db_pool.putconn(conn)

        return stats