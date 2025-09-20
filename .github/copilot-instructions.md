# Stealer-Parser AI Coding Conventions

This document provides guidance for AI agents to effectively contribute to the `stealer-parser` codebase.

## Architecture Overview

The application is a command-line tool that parses information stealer log archives (`.zip`, `.rar`, `.7z`) and extracts structured data (credentials, system info). The core architecture relies on dependency injection, a pluggable parsing system, and services for processing and exporting data.

- **Entrypoint**: `stealer_parser/main.py` handles CLI arguments, file reading, and orchestrates the main workflow.
- **Dependency Injection**: The project uses the `dependency-injector` library. All major components are wired together in `stealer_parser/containers.py`. The main container is `AppContainer`. When adding new services or components, they should be registered here.
- **Parsing Engine**: The parsing logic is central to this project. It uses `PLY` (Python Lex-Yacc) for lexing and parsing.
    - **Parsers**: Individual parsers are located in `stealer_parser/parsing/parsers/`. Each parser is responsible for a specific log file format.
    - **Grammars**: The grammars that `PLY` uses are defined as docstrings within the parser classes (e.g., `p_credentials`, `p_error`).
    - **Parser Registry**: `stealer_parser/parsing/registry.py` automatically discovers and registers all available parsers. New parsers must inherit from `stealer_parser.parsing.parser.Parser` to be registered.
- **Services**: Business logic is encapsulated in services within the `stealer_parser/services/` directory.
    - `LeakProcessor`: Orchestrates the parsing of an entire archive by iterating through its files and delegating to the `ParserRegistry` to find the appropriate parser.
    - `PostgreSQLExporter`: Handles exporting the parsed data to a PostgreSQL database.
- **Data Models**: `Pydantic` models are used for data structures. Key models like `Credential`, `System`, and `Leak` are in `stealer_parser/models/`.
- **Configuration**: Application settings are managed via `pydantic-settings` in `stealer_parser/config.py`.

## Developer Workflow

- **Setup**: The project uses `Poetry` for dependency management.
  1.  Install dependencies: `poetry install`
  2.  Activate virtual environment: `poetry shell`

- **Running the tool**: The main script can be run directly.
  ```bash
  stealer_parser <archive_file> [options]
  ```

- **Testing**: The project uses `pytest`.
  - Run all tests: `poetry run pytest`
  - Test files are located in the `tests/` directory and follow the `test_*.py` naming convention.

## Key Conventions

- **Dependency Injection**: Do not instantiate classes directly. Instead, inject them using the containers defined in `stealer_parser/containers.py`. Use `@inject` decorators on functions and methods that require dependencies.
- **Creating New Parsers**:
  1.  Create a new file in `stealer_parser/parsing/parsers/`.
  2.  Define a class that inherits from `stealer_parser.parsing.parser.Parser`.
  3.  Set the `tokens` class attribute.
  4.  Implement lexer rules as methods with names like `t_WORD`.
  5.  Implement yacc grammar rules as methods with names like `p_rule`. The docstring of the method defines the grammar.
  6.  The parser will be automatically registered.
- **Error Handling**: Parsers should handle parsing errors in a `p_error` method. The `LeakProcessor` will catch exceptions and log them.
- **Database Interaction**: Database logic is handled through Data Access Objects (DAOs) in `stealer_parser/database/dao/`. When adding new database interactions, create or update a DAO. All database components are managed in `stealer_parser/database/postgres.py` and the `DatabaseContainer`.
- **Logging**: A `VerboseLogger` instance is injected from the `AppContainer`. Use this logger for all logging.
