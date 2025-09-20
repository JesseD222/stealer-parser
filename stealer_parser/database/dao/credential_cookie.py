"""DAO for complex queries involving credentials and cookies."""
from typing import Any, List

from .base import BaseDAO


class CredentialCookieDAO(BaseDAO):
    """DAO for finding matching credentials and cookies."""

    def find_matches(self, host_pattern: str) -> List[Any]:
        """
        Find credentials matching host pattern and their associated cookies.

        Parameters
        ----------
        host_pattern : str
            The host pattern to search for in credential hosts and cookie domains.

        Returns
        -------
        List[Any]
            A list of rows, where each row is a dictionary-like object
            containing system, credential, and cookie information.
        """
        query = """
        SELECT
            -- System information
            s.id as system_id,
            s.machine_id,
            s.computer_name,
            s.hardware_id,
            s.machine_user,
            s.ip_address,
            s.country,

            -- Credentials information
            c.id as credential_id,
            c.software,
            c.host,
            c.username,
            c.password,
            c.domain as credential_domain,
            c.filepath as credential_filepath,
            c.stealer_name as credential_stealer_name,

            -- Cookies information (may be NULL if no matching cookies)
            ck.id as cookie_id,
            ck.domain as cookie_domain,
            ck.domain_specified,
            ck.path,
            ck.secure,
            ck.expiry,
            ck.name as cookie_name,
            ck.value as cookie_value,
            ck.browser,
            ck.profile,
            ck.filepath as cookie_filepath,
            ck.stealer_name as cookie_stealer_name

        FROM systems s
        INNER JOIN credentials c ON s.id = c.system_id
        LEFT JOIN cookies ck ON s.id = ck.system_id AND ck.domain LIKE %(host_pattern)s
        WHERE c.host LIKE %(host_pattern)s
        ORDER BY s.id, c.id, ck.id;
        """
        return self._execute_query(query, {"host_pattern": f"%{host_pattern}%"}, fetch="all")

    def insert(self, *args: Any) -> int:
        """Not implemented for this read-only DAO."""
        raise NotImplementedError("This is a read-only DAO.")
