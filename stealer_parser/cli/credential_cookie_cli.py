"""Component for finding matching credentials and cookies and exporting cook    def connect(self) -> None:
ie jars.
This component queries the database for credentials matching a specified host pattern,
finds cookies from the same systems that match the host pattern in their domain,
and exports the cookies in Netscape cookie jar format.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from verboselogs import VerboseLogger

from stealer_parser.containers import AppContainer
from stealer_parser.services.credential_cookie_matcher import CredentialCookieMatch


def export_cookies_to_jar(
    matches: List[CredentialCookieMatch], 
    output_dir: Path,
    logger: VerboseLogger,
    filename_template: str = "{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt"
) -> List[Path]:
    """Export cookies for each credential match to separate Netscape cookie jar files.
    
    Parameters
    ----------
    matches : List[CredentialCookieMatch]
        The credential-cookie matches to export.
    output_dir : Path
        Directory to save the cookie jar files.
    logger : VerboseLogger
        Logger instance for debugging.
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
            logger.debug(f"No cookies found for credential {match.credential_id} on system {match.system_id}")
            continue
        
        # Create safe filename
        safe_host = _sanitize_filename(match.host)
        safe_username = _sanitize_filename(match.username)
        safe_computer = _sanitize_filename(match.computer_name)
        safe_ip = _sanitize_filename(match.ip_address)
        
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
        _write_netscape_cookie_jar(match, output_path)
        created_files.append(output_path)
        
        logger.info(f"Exported {len(match.cookies)} cookies to {output_path}")
    
    return created_files

def _write_netscape_cookie_jar(match: CredentialCookieMatch, output_path: Path) -> None:
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
            domain_specified = _format_boolean(cookie['domain_specified'])
            path = cookie['path'] or '/'
            secure = _format_boolean(cookie['secure'])
            expiry = _format_expiry(cookie['expiry'])
            name = cookie['name'] or ''
            value = cookie['value'] or ''
            
            # Write tab-delimited line
            line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n"
            f.write(line)

def _format_boolean(value: str) -> str:
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

def _format_expiry(expiry: str) -> str:
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

def _sanitize_filename(filename: str) -> str:
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

def get_summary_report(matches: List[CredentialCookieMatch]) -> str:
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
    """Main function to run the credential-cookie matcher CLI."""
    # Setup argument parser
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
    parser.add_argument("--db-name", default="derp", help="Database name")
    parser.add_argument("--db-user", default="derp", help="Database user")
    parser.add_argument("--db-password", default="disforderp", help="Database password")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--config", 
        type=Path, 
        default=Path("./config.yaml"),
        help="Path to the configuration file (default: ./config.yaml)"
    )
    args = parser.parse_args()

    # Initialize container and wire modules
    container = AppContainer()
    config = container.config()
    
    # The pydantic-settings model loads from .env automatically.
    # We just need to override with CLI args.
    
    # Override config with CLI args if provided
    if args.db_host:
        config.db_host = args.db_host
    if args.db_port:
        config.db_port = args.db_port
    if args.db_name:
        config.db_name = args.db_name
    if args.db_user:
        config.db_user = args.db_user
    if args.db_password:
        config.db_password = args.db_password

    # Setup logger
    log_level = "verbose" if args.verbose else "info"
    logging.basicConfig(level=log_level.upper())
    logger = VerboseLogger(__name__)
    logger.setLevel(log_level.upper())
    container.logger.override(logger)
    
    container.wire(modules=[__name__])

    # Get service from container
    matcher = container.services.credential_cookie_matcher()

    # Find matches
    matches = matcher.find_matching_credentials_and_cookies(args.host_pattern)

    if not matches:
        logger.info("No matches found.")
        sys.exit(0)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export cookies and generate report
    export_cookies_to_jar(matches, output_dir, logger)
    summary = get_summary_report(matches)

    # Write summary report
    report_path = output_dir / "summary_report.txt"
    report_path.write_text(summary)

    logger.info(f"Export complete. Summary report saved to: {report_path}")
    logger.info(f"\n{summary}")


if __name__ == "__main__":
    main()