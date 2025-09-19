#!/usr/bin/env python3
"""
CLI tool for finding and exporting matching credentials and cookies.

This command-line tool searches for credentials matching a specified host pattern
and exports their associated cookies as Netscape cookie jar files.
"""

import argparse
import logging
import sys
from pathlib import Path

from stealer_parser.containers import Container
from stealer_parser.credential_cookie_matcher import CredentialCookieMatcher
from verboselogs import VerboseLogger


def setup_logging(verbose: bool = False) -> VerboseLogger:
    """Set up logging configuration.
    
    Parameters
    ----------
    verbose : bool, default=False
        Enable verbose logging output.
        
    Returns
    -------
    VerboseLogger
        Configured logger instance.
    """
    logger = VerboseLogger("credential-cookie-cli")
    
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Create console handler with formatting
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns
    -------
    argparse.Namespace
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Find credentials and cookies matching a host pattern and export as cookie jars",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s paypal.com ./paypal_exports
  %(prog)s stake.us ./stake_exports --db-host localhost --db-user postgres
  %(prog)s github.com ./github_exports --verbose --filename-template "github_{ip_address}_{username}_cookies.txt"
        """
    )
    
    # Required arguments
    parser.add_argument(
        "host_pattern", 
        help="Host pattern to search for (e.g., 'paypal.com', 'stake.us', 'github.com')"
    )
    parser.add_argument(
        "output_path", 
        type=Path,
        help="Directory path where cookie jar files will be exported"
    )
    
    # Database connection options
    db_group = parser.add_argument_group('Database Connection')
    db_group.add_argument(
        "--db-host", 
        default="localhost", 
        help="Database host (default: localhost)"
    )
    db_group.add_argument(
        "--db-port", 
        type=int, 
        default=5432, 
        help="Database port (default: 5432)"
    )
    db_group.add_argument(
        "--db-name", 
        default="derp", 
        help="Database name (default: stealer_parser)"
    )
    db_group.add_argument(
        "--db-user", 
        default="derp", 
        help="Database user (default: postgres)"
    )
    db_group.add_argument(
        "--db-password", 
        default="disforderp", 
        help="Database password (default: empty)"
    )
    
    # Export options
    export_group = parser.add_argument_group('Export Options')
    export_group.add_argument(
        "--filename-template",
        default="{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt",
        help="Template for cookie jar filenames (default: {system_id}_{ip_address}_{credential_id}_{host}_cookies.txt)"
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output with debug information"
    )
    output_group.add_argument(
        "--quiet", 
        action="store_true", 
        help="Suppress summary report output (only show file creation messages)"
    )
    output_group.add_argument(
        "--no-summary", 
        action="store_true", 
        help="Skip printing the detailed summary report"
    )
    
    return parser.parse_args()


def main() -> int:
    """Main CLI entry point.
    
    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    container = Container()
    container.wire(modules=[sys.modules[__name__]])
    
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # Override config with CLI arguments
    config_overrides = {
        "db_host": args.db_host,
        "db_port": args.db_port,
        "db_name": args.db_name,
        "db_user": args.db_user,
        "db_password": args.db_password,
    }
    container.config.override(config_overrides)
    
    # Validate arguments
    if not args.host_pattern.strip():
        logger.error("Host pattern cannot be empty")
        return 1
    
    try:
        # Initialize the matcher from the container
        logger.info(f"Connecting to database {container.config.db_name()} on {container.config.db_host()}:{container.config.db_port()}")
        matcher: CredentialCookieMatcher = container.credential_cookie_matcher()
        matcher.logger = logger  # Assign logger
        
        # Search for matches
        logger.info(f"Searching for credentials and cookies matching: '{args.host_pattern}'")
        matches = matcher.find_matching_credentials_and_cookies(args.host_pattern)
        
        if not matches:
            logger.warning(f"No matches found for host pattern: '{args.host_pattern}'")
            logger.info("Try using a different pattern or check your database contents")
            return 1
        
        logger.info(f"Found {len(matches)} credential-cookie matches")
        
        # Print summary report unless suppressed
        if not args.no_summary and not args.quiet:
            print("\n" + "="*60)
            summary = matcher.get_summary_report(matches)
            print(summary)
            print("="*60 + "\n")
        
        # Create output directory
        args.output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Exporting cookies to: {args.output_path}")
        
        # Export cookie jars
        created_files = matcher.export_cookies_to_jar(
            matches, 
            args.output_path,
            filename_template=args.filename_template
        )
        
        # Report results
        logger.info(f"Successfully created {len(created_files)} cookie jar files:")
        for file_path in created_files:
            if args.verbose:
                # Get file size for verbose output
                file_size = file_path.stat().st_size if file_path.exists() else 0
                logger.info(f"  - {file_path} ({file_size} bytes)")
            else:
                logger.info(f"  - {file_path}")
        
        if not args.quiet:
            print(f"\n✅ Export completed successfully!")
            print(f"📁 Location: {args.output_path}")
            print(f"📄 Files created: {len(created_files)}")
            total_cookies = sum(len(match.cookies) for match in matches)
            print(f"🍪 Total cookies exported: {total_cookies}")
        
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
        # The container will manage the connection pool lifecycle
        pass


if __name__ == "__main__":
    sys.exit(main())