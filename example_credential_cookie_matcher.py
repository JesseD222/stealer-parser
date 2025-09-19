#!/usr/bin/env python3
"""
Example script demonstrating the CredentialCookieMatcher component.

This script shows how to use the CredentialCookieMatcher to find credentials
and cookies matching a specific host pattern and export them as cookie jar files.
"""

from pathlib import Path
from stealer_parser.credential_cookie_matcher import CredentialCookieMatcher
from verboselogs import VerboseLogger


def example_usage():
    """Example of how to use the CredentialCookieMatcher."""
    
    # Set up logging
    logger = VerboseLogger("example")
    logger.setLevel("INFO")
    
    # Initialize the matcher with database connection parameters
    matcher = CredentialCookieMatcher(
        logger=logger,
        host="localhost",
        port=5432,
        database="derp",
        user="derp",
        password="disforderp"  # Set your password here
    )
    
    try:
        # Example 1: Search for stake.us credentials and cookies
        print("=== Example 1: Searching for stake.us ===")
        host_pattern = "paypal.com"
        
        matches = matcher.find_matching_credentials_and_cookies(host_pattern)
        
        if matches:
            # Print summary report
            summary = matcher.get_summary_report(matches)
            print(summary)
            
            # Export cookies to files
            output_dir = Path("./exports")
            created_files = matcher.export_cookies_to_jar(matches, output_dir)
            
            print(f"\nCreated {len(created_files)} cookie jar files:")
            for file_path in created_files:
                print(f"  - {file_path}")
        else:
            print(f"No matches found for {host_pattern}")
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Error during example execution: {e}")
        raise
    finally:
        matcher.disconnect()


if __name__ == "__main__":
    example_usage()