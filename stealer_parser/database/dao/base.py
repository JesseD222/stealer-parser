"""Abstract base classes and protocols for database interactions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.pool import SimpleConnectionPool
from verboselogs import VerboseLogger

from stealer_parser.models.cookie import Cookie
from stealer_parser.models.credential import Credential
from stealer_parser.models.leak import Leak
from stealer_parser.models.system import System

from psycopg2.extras import execute_values


class BaseDAO(ABC):
    """Abstract Base Class for Data Access Objects."""

    def __init__(self, db_pool: SimpleConnectionPool, logger: Optional[VerboseLogger] = None):
        self.db_pool = db_pool
        self.logger = logger or VerboseLogger(__name__)
        if execute_values is None:
            self.logger.warning("psycopg2.extras.execute_values not found. Bulk inserts will be slow.")

    @abstractmethod
    def insert(self, *args: Any) -> int:
        """Insert a single data object and return its ID."""
        raise NotImplementedError

    def bulk_insert(self, *args: Any) -> int:
        """Insert multiple data objects and return the number of inserted rows."""
        raise NotImplementedError

    def _execute_query(
        self,
        query: str,
        params: Tuple | Dict = (),
        fetch: Optional[str] = None,
        conn=None,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a query and return results.

        If a connection is provided, it will be used without committing; the caller manages transactions.
        If not provided, a connection is acquired from the pool and committed per call.
        """
        own_conn = False
        try:
            if conn is None:
                conn = self.db_pool.getconn()
                own_conn = True
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if own_conn:
                    conn.commit()
                if fetch == "one":
                    return cursor.fetchone()
                if fetch == "all":
                    return cursor.fetchall()
                return cursor.rowcount
        except Exception as e:
            if conn and own_conn:
                conn.rollback()
            ctx_str = self._fmt_ctx(ctx)
            self.logger.error(
                f"db_error op=execute_query fetch={fetch} own_conn={own_conn} {ctx_str}err={e}"
            )
            raise
        finally:
            if conn and own_conn:
                self.db_pool.putconn(conn)

    def _execute_values(
        self,
        query: str,
        data: List[Tuple],
        conn=None,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Execute a query with a list of tuples using execute_values.

        Honors the same external connection semantics as _execute_query.
        """
        if not execute_values:
            # Fallback to individual inserts if execute_values is not available
            return sum(
                self._execute_query(
                    query.replace("%s", "(" + ",".join(["%s"] * len(d)) + ")"),
                    d,
                    conn=conn,
                    ctx=ctx,
                )
                for d in data
            )

        own_conn = False
        try:
            if conn is None:
                conn = self.db_pool.getconn()
                own_conn = True
            with conn.cursor() as cursor:
                execute_values(cursor, query, data)
                if own_conn:
                    conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn and own_conn:
                conn.rollback()
            ctx_rows = len(data) if isinstance(data, list) else "unknown"
            ctx_str = self._fmt_ctx(ctx)
            self.logger.error(
                f"db_error op=execute_values rows={ctx_rows} own_conn={own_conn} {ctx_str}err={e}"
            )
            raise
        finally:
            if conn and own_conn:
                self.db_pool.putconn(conn)

    def _fmt_ctx(self, ctx: Optional[Dict[str, Any]]) -> str:
        if not ctx:
            return ""
        parts: List[str] = []
        for k, v in ctx.items():
            # Avoid None and overly long values; keep logs readable and safe
            if v is None:
                continue
            s = str(v)
            if len(s) > 256:
                s = s[:253] + "..."
            parts.append(f"{k}={s}")
        return (" ".join(parts) + " ") if parts else ""


class LeaksDAO(BaseDAO):
    """DAO for leaks."""

    def insert(self, *args: Any, conn=None) -> int:
        data: Leak = args[0]
        query = "INSERT INTO leaks (filename) VALUES (%s) RETURNING id;"
        result = self._execute_query(
            query,
            (data.filename,),
            fetch="one",
            conn=conn,
            ctx={"dao": "LeaksDAO", "action": "insert", "table": "leaks", "filename": data.filename},
        )
        return result[0]

    def update_counts(self, leak_id: int, systems_count: int, conn=None) -> None:
        query = "UPDATE leaks SET systems_count = %s WHERE id = %s;"
        self._execute_query(
            query,
            (systems_count, leak_id),
            conn=conn,
            ctx={
                "dao": "LeaksDAO",
                "action": "update_counts",
                "table": "leaks",
                "leak_id": leak_id,
                "systems_count": systems_count,
            },
        )


class SystemsDAO(BaseDAO):
    """DAO for systems."""

    def insert(self, *args: Any, conn=None) -> int:
        data: System = args[0]
        leak_id: int = args[1]
        query = """
        INSERT INTO systems (leak_id, machine_id, computer_name, hardware_id, machine_user, ip_address, country, log_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        params = (
            leak_id,
            data.machine_id,
            data.computer_name,
            data.hardware_id,
            data.machine_user,
            data.ip_address,
            data.country,
            data.log_date,
        )
        result = self._execute_query(
            query,
            params,
            fetch="one",
            conn=conn,
            ctx={
                "dao": "SystemsDAO",
                "action": "insert",
                "table": "systems",
                "leak_id": leak_id,
                "machine_id": data.machine_id,
            },
        )
        return result[0]


class CredentialsDAO(BaseDAO):
    """DAO for credentials."""

    def insert(self, *args: Any, conn=None) -> int:
        data: Credential = args[0]
        system_id: int = args[1]
        query = """
        INSERT INTO credentials (system_id, software, host, username, password, domain, local_part, email_domain, filepath, stealer_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            system_id,
            data.software,
            data.host,
            data.username,
            data.password,
            data.domain,
            data.local_part,
            data.email_domain,
            str(data.filepath),
            data.stealer_name,
        )
        return self._execute_query(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "CredentialsDAO",
                "action": "insert",
                "table": "credentials",
                "system_id": system_id,
                "host": data.host,
                "filepath": str(data.filepath),
            },
        )

    def bulk_insert(self, *args: Any, conn=None) -> int:
        data: List[Credential] = args[0]
        system_id: int = args[1]
        query = """
        INSERT INTO credentials (system_id, software, host, username, password, domain, local_part, email_domain, filepath, stealer_name)
        VALUES %s;
        """
        params = [
            (
                system_id,
                cred.software,
                cred.host,
                cred.username,
                cred.password,
                cred.domain,
                cred.local_part,
                cred.email_domain,
                str(cred.filepath),
                cred.stealer_name,
            )
            for cred in data
        ]
        return self._execute_values(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "CredentialsDAO",
                "action": "bulk_insert",
                "table": "credentials",
                "system_id": system_id,
                "rows": len(data),
            },
        )


class CookiesDAO(BaseDAO):
    """DAO for cookies."""

    def insert(self, *args: Any, conn=None) -> int:
        data: Cookie = args[0]
        system_id: int = args[1]
        query = """
        INSERT INTO cookies (system_id, domain, domain_specified, path, secure, expiry, name, value, browser, profile, filepath, stealer_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            system_id,
            data.domain,
            data.domain_specified,
            data.path,
            data.secure,
            data.expiry,
            data.name,
            data.value,
            data.browser,
            data.profile,
            str(data.filepath),
            data.stealer_name,
        )
        return self._execute_query(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "CookiesDAO",
                "action": "insert",
                "table": "cookies",
                "system_id": system_id,
                "domain": data.domain,
                "filepath": str(data.filepath),
            },
        )

    def bulk_insert(self, *args: Any, conn=None) -> int:
        data: List[Cookie] = args[0]
        system_id: int = args[1]
        query = """
        INSERT INTO cookies (system_id, domain, domain_specified, path, secure, expiry, name, value, browser, profile, filepath, stealer_name)
        VALUES %s;
        """
        params = [
            (
                system_id,
                cookie.domain,
                cookie.domain_specified,
                cookie.path,
                cookie.secure,
                cookie.expiry,
                cookie.name,
                cookie.value,
                cookie.browser,
                cookie.profile,
                str(cookie.filepath),
                cookie.stealer_name,
            )
            for cookie in data
        ]
        return self._execute_values(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "CookiesDAO",
                "action": "bulk_insert",
                "table": "cookies",
                "system_id": system_id,
                "rows": len(data),
            },
        )
