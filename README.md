# Infostealer logs parser

Information stealers are malwares that steal sensitive data, aka **logs**, to be sold in forums or shared in chat groups.

This tool takes a **logs archive**, parses it, and exports to a PostgreSQL database by default, with optional JSON output.

## Table of Content

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [License](#license)

## Features

- Accepts the following **archive formats**: `.rar`, `.zip`, `.7z`.
  Please note that multi-parts ZIP files aren't handled yet.
- Parses files containing credentials and information about compromised systems.
- Outputs result as **JSON** or **PostgreSQL database**.

### Output Options

- **PostgreSQL Database** (default): Direct export for advanced querying and analysis
- **JSON Export** (optional via `--dump-json`): Structured JSON files for easy integration

See [Database Export Documentation](docs/database_export.md) for detailed database setup and usage instructions.

### Result

The following data are extracted:

- [Credential](stealer_parser/models/credential.py)

  - **software**: Web browser or email client.
  - **host**: Hostname or URL visited by user.
  - **username**: Username or email address.
  - **password**: Password.
  - **domain**: Domain name extracted from host/URL.
  - **local_part**: The part before the @ in an email address.
  - **email_domain**: Domain name extracted from email address.
  - **filepath**: The credential file path.
  - **stealer_name**: The stealer that harvested the data.

- [System](stealer_parser/models/system.py)

  - **machine_id**: The device ID (UID or machine ID).
  - **computer_name**: The machine's name.
  - **hardware_id**: The hardware ID (HWID).
  - **machine_user**: The machine user's name.
  - **ip_address**: The machine IP address.
  - **country**: The machine's country code.
  - **log_date**: The compromission date.

### Parsing errors

If a file can't be parsed, it will be saved into the `logs` folder as well as a `<filename>.log` text file containing the parsing related error message.

## Requirements

- Python 3.10 or greater
- [`Poetry`](https://python-poetry.org/)

## Installation

1. Clone the repository including its submodules and change it to your working directory.

```console
$ git clone --recurse-submodules https://github.com/lexfo/stealer-parser
```

2. Install the project:

```console
$ poetry install
```

3. Activate the virtual environment:

```console
$ poetry shell
```

## Environment Setup

Use the provided `.env.example` to configure database and parser behavior. Copy it and adjust values:

```bash
cp .env.example .env
```

Key variables:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL connection.
- `DB_CREATE_TABLES`: `true|false` to recreate schema before export.
- `PREFER_DEFINITION_PARSERS`: `true|false` to prefer YAML definition parsers.
- `RECORD_DEFINITIONS_DIRS`: Comma-separated directories for YAML definitions.
- `PARSER_MATCH_THRESHOLD`: Float threshold for definition matching confidence.

Quick .env template:

```dotenv
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=derp
DB_USER=derp
DB_PASSWORD=disforderp
DB_CREATE_TABLES=false

# Parser
PREFER_DEFINITION_PARSERS=false
RECORD_DEFINITIONS_DIRS=record_definitions
PARSER_MATCH_THRESHOLD=0.15
```

## Usage

```console
stealer_parser [-h] [-p ARCHIVE_PASSWORD] [--dump-json FILENAME.json] [-v] filename

Parse infostealer logs archives.

positional arguments:
  filename              the archive to process (handled extensions: .rar, .zip, .7z)

options:
  -h, --help            show this help message and exit
  -p ARCHIVE_PASSWORD, --password ARCHIVE_PASSWORD
                        the archive's password if required
  --dump-json FILENAME.json
                        also write parsed output to this JSON file
  -v, --verbose         increase logs output verbosity (default: info, -v: verbose, -vv: debug, -vvv: spam)
```

Basic use (DB export by default):

```console
$ stealer_parser myfile.rar
2024-07-08 13:37:00 - StealerParser - INFO - Processing: myfile.rar ...
2024-07-08 13:37:00 - StealerParser - INFO - Exporting myfile.rar to database...
2024-07-08 13:37:00 - StealerParser - INFO - Database export completed successfully: 3 systems, 192 credentials, 156 cookies, 0 vaults, 0 user_files exported
```

Use the verbose option to display extra information:

```console
$ stealer_parser -vvv myfile.zip
2024-07-08 13:37:00 - StealerParser - INFO - Processing: myfile.zip ...
2024-07-08 13:37:00 - StealerParser - DEBUG - Parsed 'myfile.zip' (983 systems).
2024-07-08 13:37:00 - StealerParser - INFO - Exporting myfile.zip to database...
2024-07-08 13:37:00 - StealerParser - INFO - Database export completed successfully: ...
```

Open password-protected archives:

```console
$ stealer_parser myfile.zip --password mypassword
```

Also dump JSON:

```console
$ stealer_parser myfile.zip --dump-json results/foo.json
```

### Database Export

By default, results are exported to PostgreSQL using settings from `.env` or environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). See `docs/database_export.md` for full details.

Enable schema creation on startup via `.env`:

```
DB_CREATE_TABLES=true
```

Also dump JSON alongside DB export:

```console
$ stealer_parser myfile.rar --dump-json ./results/foo.json
```

## Documentation

The grammars and feature docs can be found in the [`docs` directory](docs). See [Database Export Documentation](docs/database_export.md) for DB setup, performance, logging, and troubleshooting.

## Contributing

If you want to contribute to development, please read these [guidelines](CONTRIBUTING.md).

## Acknowledgements

Lexing and parsing made easier thanks to [`PLY`](https://github.com/dabeaz/ply) by **David Beazley**.

## License

This project is licensed under [Apache License 2.0](LICENSE.md).
