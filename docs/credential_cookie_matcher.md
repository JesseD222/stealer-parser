# Credential-Cookie Matcher Component

This component finds credentials matching a specified host pattern and retrieves all associated cookies from the same compromised systems, then exports the cookies in standard Netscape cookie jar format.

## Features

- **Database Integration**: Queries PostgreSQL database for credentials and cookies
- **Pattern Matching**: Flexible host pattern matching for both credentials and cookie domains
- **Deduplication**: Automatically deduplicates cookies based on domain, name, and path
- **Grouping**: Groups results by system and credential for organized output
- **Export**: Exports cookies in standard Netscape cookie jar text format
- **Reporting**: Provides detailed summary reports of matches found

## Usage

### Basic Usage

```python
from stealer_parser.credential_cookie_matcher import CredentialCookieMatcher
from pathlib import Path

# Initialize matcher
matcher = CredentialCookieMatcher(
    host="localhost",
    port=5432,
    database="stealer_parser",
    user="postgres",
    password="your_password"
)

# Find matches for a specific host
matches = matcher.find_matching_credentials_and_cookies("stake.us")

# Export cookies to jar files
output_dir = Path("./cookie_exports")
created_files = matcher.export_cookies_to_jar(matches, output_dir)

# Get summary report
summary = matcher.get_summary_report(matches)
print(summary)

# Clean up
matcher.disconnect()
```

### Command Line Usage

```bash
# Basic usage
python -m stealer_parser.credential_cookie_matcher stake.us

# With custom database settings
python -m stealer_parser.credential_cookie_matcher stake.us \
    --output-dir ./my_exports \
    --verbose

# Example with different host patterns
python -m stealer_parser.credential_cookie_matcher github.com
python -m stealer_parser.credential_cookie_matcher facebook.com
python -m stealer_parser.credential_cookie_matcher binance.com
```

### Example Script

Run the included example script:

```bash
python example_credential_cookie_matcher.py
```

## Output Format

### Cookie Jar Files

The component exports cookies in standard Netscape cookie jar format with the following structure:

```
# Netscape HTTP Cookie File
# Extracted from system: DESKTOP-ABC123 (192.168.1.100)
# Machine ID: PC-12345-ABC-DEF
# Hardware ID: HW-98765-XYZ-789
# User: john_doe
# Credential: user@stake.us @ https://stake.us
# Password: mySecretPassword123
# Software: Chrome
# This is a generated file!  Do not edit.

.stake.us	TRUE	/	FALSE	1640995200	session_token	abc123def456
stake.us	FALSE	/api	TRUE	1640995200	csrf_token	xyz789uvw012
```

### Summary Report

```
=== Credential-Cookie Match Summary ===
Total Systems: 3
Total Credentials: 5
Total Cookies: 23

=== Details by System ===
System 1: DESKTOP-ABC123 (192.168.1.100)
  Machine ID: PC-12345-ABC-DEF
  Hardware ID: HW-98765-XYZ-789
  User: john_doe
  Credentials: 2
  Cookies: 15

    • user@stake.us @ https://stake.us (Password: myPassword123) (8 cookies)
    • john.doe@stake.us @ https://stake.us/login (Password: secretPass456) (7 cookies)

System 2: LAPTOP-XYZ789 (10.0.0.50)
  Machine ID: LT-67890-GHI-JKL
  Hardware ID: HW-54321-MNO-456
  User: jane_smith
  Credentials: 1
  Cookies: 5

    • jane@stake.us @ https://stake.us (Password: password789) (5 cookies)
```

## Query Logic

The component uses the following SQL logic:

1. **Credential Matching**: Finds credentials where `host` contains the specified pattern (case-insensitive)
2. **Cookie Matching**: For each system with matching credentials, finds cookies where `domain` matches:
   - Contains the pattern anywhere in the domain
  --output-dir ./my_exports \
  --verbose
   - Domain
   - Cookie name  
   - Path

## File Naming

By default, cookie jar files are named using the template:
```
{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt
```

You can customize this with the `filename_template` parameter:

```python
matcher.export_cookies_to_jar(
    matches, 
    output_dir,
    filename_template="custom_{system_id}_{ip_address}_{username}_cookies.txt"
)
```

Available template variables:
- `{system_id}` - Database system ID
- `{credential_id}` - Database credential ID  
- `{host}` - Sanitized host from credential
- `{username}` - Sanitized username from credential
- `{computer_name}` - Sanitized computer name from system
- `{ip_address}` - Sanitized IP address from system

## Requirements

- PostgreSQL database with stealer parser schema
- psycopg2-binary for database connectivity
- verboselogs for enhanced logging

## Error Handling

The component includes comprehensive error handling for:
- Database connection issues
- Missing or malformed data
- File system permissions
- Invalid characters in filenames

All errors are logged with appropriate detail levels based on verbosity settings.