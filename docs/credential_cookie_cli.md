# Credential-Cookie CLI Tool

A command-line interface for finding credentials matching a host pattern and exporting their associated cookies as Netscape cookie jar files.

## Usage

### Basic Usage

```bash
python credential_cookie_cli.py <host_pattern> <output_path>
```

### Examples

```bash
# Search for PayPal credentials and export to paypal_exports directory
python credential_cookie_cli.py paypal.com ./paypal_exports

# Search for Stake.us with custom database settings
python credential_cookie_cli.py stake.us ./stake_exports \
    

# Search GitHub with verbose output and custom filename template
python credential_cookie_cli.py github.com ./github_exports \
    --verbose \
    --filename-template "github_{ip_address}_{username}_cookies.txt"

# Quiet mode - minimal output
python credential_cookie_cli.py binance.com ./binance_exports --quiet
```

## Command Line Options

### Required Arguments

- `host_pattern` - Host pattern to search for (e.g., 'paypal.com', 'stake.us')
- `output_path` - Directory where cookie jar files will be exported

### Database Connection Options

Database connection is read from environment or `.env` managed by the main app. See `.env.example` at the project root for a complete template you can copy to `.env`.

Keys used:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### Export Options

- `--filename-template` - Template for cookie jar filenames
  - Default: `{system_id}_{ip_address}_{credential_id}_{host}_cookies.txt`
  - Available variables: `{system_id}`, `{ip_address}`, `{credential_id}`, `{host}`, `{username}`, `{computer_name}`

### Output Options

- `-v, --verbose` - Enable verbose output with debug information
- `--quiet` - Suppress summary report (only show file creation messages)
- `--no-summary` - Skip printing the detailed summary report

## Output

### Files Created

The tool creates Netscape cookie jar files with names based on the template. Default naming:
- `1_192_168_1_100_5_paypal_com_cookies.txt`
- `2_10_0_0_50_12_stake_us_cookies.txt`

### Console Output

**Normal mode:**
```
2025-09-18 10:30:15 - INFO - Connecting to database stealer_parser on localhost:5432
2025-09-18 10:30:15 - INFO - Searching for credentials and cookies matching: 'paypal.com'
2025-09-18 10:30:16 - INFO - Found 3 credential-cookie matches

============================================================
=== Credential-Cookie Match Summary ===
Total Systems: 2
Total Credentials: 3
Total Cookies: 15

=== Details by System ===
System 1: DESKTOP-ABC123 (192.168.1.100)
  Machine ID: PC-12345-ABC-DEF
  Hardware ID: HW-98765-XYZ-789
  User: john_doe
  Credentials: 2
  Cookies: 12

    • user@paypal.com @ https://paypal.com (Password: secret123) (8 cookies)
    • john.doe@paypal.com @ https://paypal.com/login (Password: mypass456) (4 cookies)
============================================================

2025-09-18 10:30:16 - INFO - Exporting cookies to: ./paypal_exports
2025-09-18 10:30:16 - INFO - Successfully created 3 cookie jar files:
2025-09-18 10:30:16 - INFO -   - ./paypal_exports/1_192_168_1_100_5_paypal_com_cookies.txt
2025-09-18 10:30:16 - INFO -   - ./paypal_exports/1_192_168_1_100_8_paypal_com_cookies.txt
2025-09-18 10:30:16 - INFO -   - ./paypal_exports/2_10_0_0_50_12_paypal_com_cookies.txt

✅ Export completed successfully!
📁 Location: ./paypal_exports
📄 Files created: 3
🍪 Total cookies exported: 15
```

**Verbose mode:** Includes debug information and file sizes

**Quiet mode:** Only shows file creation messages, no summary report

## Error Handling

The tool provides comprehensive error handling:

- Database connection errors
- Invalid host patterns
- File system permission issues
- Missing database records

All errors are logged with appropriate detail based on verbosity level.

## Integration

This CLI tool can be easily integrated into:

- Automated forensic analysis workflows
- Security research pipelines  
- Batch processing scripts
- Incident response procedures

## Requirements

- Python 3.8+
- PostgreSQL database with stealer parser schema
- psycopg2-binary for database connectivity
- verboselogs for enhanced logging

## Installation

1. Ensure you have the stealer-parser project set up
2. Install dependencies: `poetry install`
3. Make the script executable: `chmod +x credential_cookie_cli.py`
4. Run with: `python credential_cookie_cli.py <args>` or `./credential_cookie_cli.py <args>`