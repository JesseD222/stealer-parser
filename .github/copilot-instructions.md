# Copilot Instructions for Stealer Parser

## Project Overview

This is an infostealer malware logs parser that extracts credentials and system information from compressed archives (`.rar`, `.zip`, `.7z`). It uses PLY (Python Lex-Yacc) for lexical analysis and parsing of unstructured log files.

## Architecture

### Core Components

- **Main Entry Point**: `stealer_parser/main.py` - handles archive reading and orchestrates processing
- **Processing Engine**: `stealer_parser/processing.py` - identifies file types via regex patterns and routes to appropriate parsers
- **Data Models**: `stealer_parser/models/` - dataclasses for `Credential`, `System`, `Cookie`, and `Leak` structures
- **PLY Parser System**: `stealer_parser/parsing/` - lexers and parsers for extracting structured data from unformatted logs
- **Archive Wrapper**: `stealer_parser/models/archive_wrapper.py` - unified interface for different archive formats

### Data Flow

1. Archive files are opened via format-specific handlers (`RarFile`, `ZipFile`, `SevenZipFile`)
2. Files matching `FILENAMES_REGEX` in `processing.py` are categorized by type (passwords, system, cookies, etc.)
3. Text files are processed by appropriate parsers:
   - Credentials: PLY lexers (`lexer_passwords.py`, `lexer_system.py`) for complex parsing
   - Cookies: Direct Netscape cookie jar format parsing (`parsing_cookies.py`)
4. Parsed data is converted to structured data models (`Credential`, `System`, `Cookie`)
5. Results are aggregated into a `Leak` object and exported as JSON

## Key Patterns

### PLY Integration

- **Custom Lexers**: Use PLY's token-based approach with regex patterns for complex log formats (passwords, system info)
- **Direct Parsers**: Simple tab-delimited formats like Netscape cookies use direct string parsing
- **Grammar Files**: Documentation in `docs/grammar_*.txt` defines formal grammars for PLY-based parsers
- **Parser Classes**: `LogsParser` in `parsing/parser.py` converts tokens to structured objects

### Cookie Processing

- **Netscape Format**: Follows standard 7-field tab-delimited cookie jar format
- **Browser Detection**: Automatically identifies browser type from file path patterns
- **Profile Extraction**: Attempts to extract browser profile from directory structure
- **Error Resilience**: Gracefully handles malformed cookie entries

### File Type Detection

```python
# Central regex pattern for identifying relevant files
FILENAMES_REGEX: str = r"(?i).*((password(?!cracker))|(system|information|userinfo)|(\bip)|(credits|copyright|read)|(cookies?)).*\.txt"
```

### Error Handling Strategy

- Unparseable files are saved to `logs/` directory with `.log` error files
- Archive extraction errors are caught at the main level
- PLY `LexError` exceptions are handled gracefully during parsing

## Development Workflows

### Running the Parser
```bash
poetry shell
stealer_parser myfile.rar -vvv  # verbose output for debugging
stealer_parser myfile.zip --password secret --outfile results.json
```

### Testing & Development
```bash
poetry install
poetry shell
pre-commit install  # Sets up code quality hooks
```

### Adding New Stealer Support

1. Update lexer patterns in `stealer_parser/parsing/lexer_*.py`
2. Extend grammar rules following patterns in `docs/grammar_*.txt`
3. Add stealer name detection in `search_stealer_credits.py`
4. Update `StealerNameType` enum in `models/types.py`

## Project-Specific Conventions

- **Dataclass Models**: All data structures use `@dataclass` with optional fields defaulting to `None`
- **Type Aliases**: Used extensively (e.g., `StealerNameType`, `TokenType`)
- **Path Handling**: Use `pathlib.Path` objects, not string manipulation
- **Logging**: `VerboseLogger` with levels: info (-v), verbose (-vv), debug (-vvv), spam
- **JSON Export**: Custom `EnhancedJSONEncoder` handles dataclasses and datetime objects

## External Dependencies

- **PLY**: Embedded as submodule in `stealer_parser/ply/` - modify lexer/parser files here
- **Archive Libraries**: `py7zr`, `rarfile` for format-specific extraction
- **Poetry**: Dependency management and CLI script registration

## Common Debugging

- Add `dump_to_file()` calls in `helpers.py` to save intermediate parsing states
- Use `-vvv` flag to see detailed token processing
- Check `logs/parsing/` for files that failed to parse
- PLY generates `parser.out` and `parsetab.py` files for debugging grammar issues