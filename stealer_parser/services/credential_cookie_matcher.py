"""Component for finding matching credentials and cookies."""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from verboselogs import VerboseLogger

from stealer_parser.database.dao.credential_cookie import CredentialCookieDAO

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    PSYCOPG2_AVAILABLE = False


@dataclass
class CredentialCookieMatch:
    """Data class representing a matched credential with its associated cookies."""

    system_id: int
    machine_id: str
    computer_name: str
    hardware_id: str
    ip_address: str
    machine_user: str

    # Credential info
    credential_id: int
    username: str
    password: str
    host: str
    software: str
    credential_domain: str

    # Associated cookies
    cookies: List[Dict[str, Any]]


class CredentialCookieMatcher:
    """Finds credentials matching a host pattern and their associated cookies from the same system."""

    def __init__(
        self,
        credential_cookie_dao: CredentialCookieDAO,
        logger: Optional[VerboseLogger] = None,
    ) -> None:
        """Initialize the credential-cookie matcher."""
        self.logger = logger or VerboseLogger(__name__)
        self.credential_cookie_dao = credential_cookie_dao

        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for database support. "
                "Install it with: pip install psycopg2-binary"
            )

    def find_matching_credentials_and_cookies(self, host_pattern: str) -> List[CredentialCookieMatch]:
        """Find credentials matching host pattern and their associated cookies."""
        try:
            results = self.credential_cookie_dao.find_matches(host_pattern)
        except Exception as e:
            self.logger.error(f"Failed to query database for matches: {e}")
            return []

        if not results:
            self.logger.verbose("No matching credentials found.")
            return []

        grouped_data: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(lambda: defaultdict(lambda: {
            "system_info": {},
            "credential_info": {},
            "cookies": []
        }))

        for row in results:
            system_id = row['system_id']
            credential_id = row['credential_id']
            
            group = grouped_data[system_id][credential_id]

            if not group["system_info"]:
                group["system_info"] = {
                    "system_id": system_id,
                    "machine_id": row['machine_id'],
                    "computer_name": row['computer_name'],
                    "hardware_id": row['hardware_id'],
                    "ip_address": row['ip_address'],
                    "machine_user": row['machine_user'],
                }

            if not group["credential_info"]:
                group["credential_info"] = {
                    "credential_id": credential_id,
                    "username": row['username'],
                    "password": row['password'],
                    "host": row['host'],
                    "software": row['software'],
                    "credential_domain": row['credential_domain'],
                }

            if row['cookie_id']:
                cookie_data = {
                    "domain": row['cookie_domain'],
                    "domain_specified": row['domain_specified'],
                    "path": row['path'],
                    "secure": row['secure'],
                    "expiry": row['expiry'],
                    "name": row['cookie_name'],
                    "value": row['cookie_value'],
                }
                group["cookies"].append(cookie_data)

        matches = []
        for system_id, credentials in grouped_data.items():
            for credential_id, data in credentials.items():
                unique_cookies = self._deduplicate_cookies(list(data["cookies"]))
                
                sys_info = data["system_info"]
                cred_info = data["credential_info"]
                
                match = CredentialCookieMatch(
                    system_id=sys_info["system_id"],
                    machine_id=sys_info["machine_id"],
                    computer_name=sys_info["computer_name"],
                    hardware_id=sys_info["hardware_id"],
                    ip_address=sys_info["ip_address"],
                    machine_user=sys_info["machine_user"],
                    credential_id=cred_info["credential_id"],
                    username=cred_info["username"],
                    password=cred_info["password"],
                    host=cred_info["host"],
                    software=cred_info["software"],
                    credential_domain=cred_info["credential_domain"],
                    cookies=unique_cookies
                )
                matches.append(match)

        return matches

    def _deduplicate_cookies(self, cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate a list of cookies based on a tuple of their values."""
        seen = set()
        deduplicated = []
        for cookie in cookies:
            identifier = (
                cookie.get("domain"),
                cookie.get("path"),
                cookie.get("name"),
            )
            if identifier not in seen:
                seen.add(identifier)
                deduplicated.append(cookie)
        return deduplicated
