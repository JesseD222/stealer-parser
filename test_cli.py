#!/usr/bin/env python3
"""
Test script to demonstrate the credential_cookie_cli.py functionality.

This script shows example usage patterns for the CLI tool.
"""

import subprocess
import sys
from pathlib import Path


def run_cli_example():
    """Demonstrate CLI usage with example commands."""
    
    print("=== Credential-Cookie CLI Tool Demo ===\n")
    
    # Example commands that would be run
    examples = [
        {
            "description": "Basic search for PayPal credentials",
            "command": ["python", "credential_cookie_cli.py", "paypal.com", "./paypal_exports"]
        },
        {
            "description": "Search with custom database settings",
            "command": [
                "python", "credential_cookie_cli.py", "stake.us", "./stake_exports",
                "--db-host", "localhost",
                "--db-user", "derp", 
                "--db-password", "disforderp",
                "--db-name", "derp"
            ]
        },
        {
            "description": "Verbose search with custom filename template",
            "command": [
                "python", "credential_cookie_cli.py", "github.com", "./github_exports",
                "--verbose",
                "--filename-template", "github_{ip_address}_{username}_cookies.txt"
            ]
        },
        {
            "description": "Quiet mode search",
            "command": [
                "python", "credential_cookie_cli.py", "binance.com", "./binance_exports",
                "--quiet"
            ]
        }
    ]
    
    print("Here are example commands you can run:\n")
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}:")
        print(f"   {' '.join(example['command'])}")
        print()
    
    print("To test the help system:")
    print("   python credential_cookie_cli.py --help")
    print()
    
    print("To test with actual data (update database credentials as needed):")
    print("   python credential_cookie_cli.py paypal.com ./test_exports --db-user derp --db-password disforderp --db-name derp")
    print()


def test_help():
    """Test the help functionality."""
    print("=== Testing CLI Help ===\n")
    
    try:
        result = subprocess.run(
            ["python", "credential_cookie_cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print("Help output:")
        print(result.stdout)
        
        if result.returncode == 0:
            print("✅ Help command successful")
        else:
            print("❌ Help command failed")
            print("Error:", result.stderr)
            
    except Exception as e:
        print(f"❌ Error running help command: {e}")


def main():
    """Main function."""
    print("Credential-Cookie CLI Tool Test\n")
    
    # Check if CLI file exists
    cli_path = Path("credential_cookie_cli.py")
    if not cli_path.exists():
        print(f"❌ CLI script not found: {cli_path}")
        print("Make sure you're running this from the stealer-parser directory")
        return 1
    
    # Show examples
    run_cli_example()
    
    # Test help
    test_help()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())