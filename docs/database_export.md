# PostgreSQL Database Output Component

This document describes how to use the PostgreSQL database output component for the stealer parser.

## Overview

The database output component exports parsed stealer data directly to a PostgreSQL database by default. Configuration comes from environment variables or a `.env` file, with optional JSON dumps.

## Features

- **Structured Data Storage**: Organizes credentials, system information, and cookies in normalized database tables
- **Relationship Management**: Maintains proper foreign key relationships between leaks, systems, credentials, and cookies
- **Batch Processing**: Efficiently inserts large amounts of data using batch operations
- **Error Handling**: Comprehensive error handling with transaction rollback on failures
- **Connection Management**: Automatic connection management with context manager support
- **Structured Logging**: Context-rich logs for exporter and DAO operations to speed up triage

## Prerequisites

### Database Setup

1. Install PostgreSQL server
2. Create a database for the stealer parser:
   ```sql
   CREATE DATABASE stealer_parser;
   ```

### Python Dependencies

Install the PostgreSQL adapter:
```bash
poetry install  # Installs psycopg2-binary automatically
```

Or manually:
```bash
pip install psycopg2-binary
```

## Database Schema

The component creates four main tables:

### `leaks`
- `id` (SERIAL PRIMARY KEY): Unique leak identifier
- `filename` (VARCHAR): Original archive filename
- `created_at` (TIMESTAMP): When the leak was processed
- `systems_count` (INTEGER): Number of systems in this leak

### `systems`
- `id` (SERIAL PRIMARY KEY): Unique system identifier
- `leak_id` (INTEGER): Foreign key to leaks table
- `machine_id` (VARCHAR): Device ID or machine ID
- `computer_name` (VARCHAR): Machine name
- `hardware_id` (VARCHAR): Hardware ID (HWID)
- `machine_user` (VARCHAR): Machine user name
- `ip_address` (INET): Machine IP address
- `country` (VARCHAR): Country code
- `log_date` (VARCHAR): Compromise date
- `created_at` (TIMESTAMP): Record creation time

### `credentials`
- `id` (SERIAL PRIMARY KEY): Unique credential identifier
- `system_id` (INTEGER): Foreign key to systems table
- `software` (VARCHAR): Browser or software name
- `host` (TEXT): URL or hostname
- `username` (VARCHAR): Username or email
- `password` (TEXT): Password
- `domain` (VARCHAR): Extracted domain name
- `local_part` (VARCHAR): Email local part
- `email_domain` (VARCHAR): Email domain
- `filepath` (TEXT): Original file path
- `stealer_name` (VARCHAR): Stealer malware name
- `created_at` (TIMESTAMP): Record creation time

### `cookies`
- `id` (SERIAL PRIMARY KEY): Unique cookie identifier
- `system_id` (INTEGER): Foreign key to systems table
- `domain` (VARCHAR): Cookie domain
- `domain_specified` (VARCHAR): Domain specification flag
- `path` (TEXT): Cookie path
- `secure` (VARCHAR): Security flag
- `expiry` (VARCHAR): Expiration date
- `name` (VARCHAR): Cookie name
- `value` (TEXT): Cookie value
- `browser` (VARCHAR): Browser name
- `profile` (VARCHAR): Browser profile
- `filepath` (TEXT): Original file path
- `stealer_name` (VARCHAR): Stealer malware name
- `created_at` (TIMESTAMP): Record creation time

## Usage

### Basic Database Export

By default the parser exports to PostgreSQL. To also dump JSON:

```bash
stealer_parser myfile.rar --dump-json results/myfile.json
```

### Custom Database Connection

Configure connection via environment or `.env` (examples):

```
DB_HOST=192.168.1.100
DB_PORT=5432
DB_NAME=stealer_parser
DB_USER=analyst
DB_PASSWORD=secret123
DB_CREATE_TABLES=false
```

See `.env.example` at the project root for a complete template you can copy to `.env`.

### Environment Variables

You can also use environment exports (e.g., `export DB_PASSWORD=secret123`).

## Configuration Keys

Available configuration keys (via environment or `.env`):

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DB_CREATE_TABLES` (true/false) — recreate schema before export

## Example Queries

Once data is exported, you can run SQL queries to analyze the data:

### Count credentials by stealer type
```sql
SELECT stealer_name, COUNT(*) as credential_count
FROM credentials 
WHERE stealer_name IS NOT NULL
GROUP BY stealer_name
ORDER BY credential_count DESC;
```

### Find systems with most credentials
```sql
SELECT s.computer_name, s.ip_address, COUNT(c.id) as cred_count
FROM systems s
LEFT JOIN credentials c ON s.id = c.system_id
GROUP BY s.id, s.computer_name, s.ip_address
ORDER BY cred_count DESC
LIMIT 10;
```

### Top domains in credentials
```sql
SELECT domain, COUNT(*) as count
FROM credentials 
WHERE domain IS NOT NULL
GROUP BY domain
ORDER BY count DESC
LIMIT 20;
```

### Find systems by country
```sql
SELECT country, COUNT(*) as system_count
FROM systems
WHERE country IS NOT NULL
GROUP BY country
ORDER BY system_count DESC;
```

## Error Handling

The component includes comprehensive error handling:

- **Connection Errors**: Clear messages for database connection issues
- **Missing Dependencies**: Helpful error when psycopg2 is not installed
- **Transaction Rollback**: Automatic rollback on any insertion error
- **Validation**: Parameter validation before attempting connection
- **Field Length Protection**: Automatic truncation of overly long data fields
- **Retry/Backoff**: Transient errors are retried with exponential backoff and jitter in the exporter
- **Batch Insert Fallback**: Falls back to individual inserts only when `psycopg2.extras.execute_values` is unavailable
- **Partial Success Handling**: Continues processing even if some records fail
- **Data Sanitization**: Safely truncates data to prevent database field overflow

### Error Recovery Features

1. **Automatic Data Truncation**: Fields that exceed database limits are automatically truncated with "..." suffix
2. **Retry with Backoff**: Transient connection/transaction errors in the exporter are retried with exponential backoff + jitter
3. **Batch Fallback (Capability)**: If `execute_values` is not available at runtime, the system falls back to individual inserts
4. **System-Level Error Isolation**: Failure to process one system doesn't stop processing of others
5. **Detailed Logging**: Comprehensive logging at multiple levels (warning, error, debug) for troubleshooting

## Performance Considerations

- **Batch Inserts**: Uses `psycopg2.extras.execute_values` for efficient bulk insertions
- **Indexing**: Automatically creates indexes on frequently queried columns
- **Transactions**: Groups related operations in transactions for consistency
- **Connection Pooling**: Consider using connection pooling for high-volume processing

## Logging

Both the exporter and DAOs emit structured, context-rich logs to aid troubleshooting:

- Exporter
   - `db_connect_ok`: logs safe connection info (host, port, dbname, user)
   - `db_retry`: attempt number, backoff seconds, and exception summary
   - `db_export_start`/`db_export_done`: filename and counts exported

- DAOs (on errors)
   - Include: `dao`, `action`, `table`, and relevant identifiers (e.g., `leak_id`, `system_id`, `machine_id`, `filename`, `filepath`, `rows`)
   - Example: `db_error op=execute_values rows=100 own_conn=True dao=CredentialsDAO action=bulk_insert table=credentials system_id=42 rows=100 err=...`

Notes
- Sensitive secrets (passwords) are never logged; only safe connection metadata and record context are included.
- Overly long values are truncated in logs to keep output readable.

## Troubleshooting

### Common Issues

1. **"psycopg2 not installed"**
   ```bash
   pip install psycopg2-binary
   ```

2. **"Failed to connect to PostgreSQL"**
   - Check PostgreSQL is running
   - Verify connection parameters
   - Check firewall settings
   - Ensure database exists

3. **"Permission denied"**
   - Verify user has CREATE TABLE permissions
   - Check database user privileges

4. **"Table already exists"**
   - Control schema creation via `DB_CREATE_TABLES` in `.env`
   - Or manually create tables using the schema

## Field Size Limits

The database schema includes reasonable field size limits to prevent abuse while accommodating most real-world data:

| Field | Table | Type | Limit | Notes |
|-------|-------|------|-------|-------|
| username | credentials | VARCHAR | 1000 chars | Accommodates very long usernames/emails |
| software | credentials | VARCHAR | 255 chars | Browser/application names |
| domain | credentials | VARCHAR | 255 chars | Domain names |
| host | credentials | TEXT | ~2000 chars* | URLs and hostnames |
| password | credentials | TEXT | ~2000 chars* | Passwords (truncated for safety) |
| computer_name | systems | VARCHAR | 255 chars | Machine names |
| machine_id | systems | VARCHAR | 255 chars | Device identifiers |

*TEXT fields are automatically truncated to 2000 characters for performance reasons

### Handling Oversized Data

When data exceeds field limits:
1. **Automatic Truncation**: Data is truncated to fit with "..." suffix
2. **Warning Logs**: Warnings are logged for truncated fields
3. **Graceful Degradation**: Processing continues with truncated data
4. **Individual Fallback**: Failed batch inserts retry individually

### Database Migration

If upgrading from an earlier version, run the migration script:

```bash
psql -d stealer_parser -f stealer_parser/database/migration_001.sql
```

### Debug Mode

Use verbose logging to diagnose issues:
```bash
stealer_parser myfile.rar -vvv
```

This increases the username field from 500 to 1000 characters.

## Integration Examples

### With Other Tools

The database output can be easily integrated with:

- **Business Intelligence tools** (Grafana, Tableau)
- **Security platforms** (SIEM systems)
- **Custom analysis scripts** (Python, R)
- **Web applications** (Django, Flask)

### Backup and Migration

Export data for backup or migration:
```bash
pg_dump stealer_parser > backup.sql
```

## Security Considerations

- Use strong database passwords
- Configure PostgreSQL authentication properly
- Consider using SSL/TLS for database connections
- Implement proper database user permissions
- Regularly backup sensitive data

## Future Enhancements

Potential improvements for future versions:

- Support for other database systems (MySQL, SQLite)
- Data deduplication logic
- Incremental updates
- Data visualization dashboards
- API endpoints for data access