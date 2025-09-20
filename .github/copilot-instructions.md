# Stealer-Parser • AI Coding Guide

Concise, project-specific guidance to help AI agents work effectively in this codebase.

## Architecture

- Entrypoint: `stealer_parser/main.py` parses CLI args, opens archives (`.rar`, `.zip`, `.7z` via `rarfile`, `zipfile`, `py7zr`), invokes `LeakProcessor`, and optionally exports to PostgreSQL.
- Dependency Injection: Wired in `stealer_parser/containers.py` using `dependency-injector`. Use `AppContainer` to resolve services; avoid manual instantiation.
- Parsing System: Hybrid model
  - PLY-based parsers in `stealer_parser/parsing/parsers/*` (e.g., `PasswordParser`, `SystemParser`) define token rules + docstring grammars.
  - Definition-driven parser (`ConfigurableParser`) built via `ParserFactory` and strategy registry. Record definitions live in `record_definitions/*.yml` and are scored/selected by `ParserRegistry.find_best_for` when `Settings.prefer_definition_parsers=True`.
- Services: `LeakProcessor` orchestrates parsing over archive file paths and aggregates `SystemData`. `PostgreSQLExporter` handles DB export via DAOs (`stealer_parser/database/dao/*`).
- Models: Dataclasses/Pydantic-like models in `stealer_parser/models/*` (e.g., `Credential`, `Cookie`, `System`, `Leak`, `Vault`).
- Config: `stealer_parser/config.py` (`pydantic-settings`) loads `.env`. Notable flags: `prefer_definition_parsers`, `record_definitions_dirs`, `parser_match_threshold`.

## Workflows

- Setup
  - `poetry install`
  - `poetry shell`
- Run parser
  - `stealer_parser <archive> [--password <pw>] [--dump-json out.json]`
  - DB export is default; configure via `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_CREATE_TABLES`).
- Cookie export CLI
  - `poetry run python -m stealer_parser.cli.credential_cookie_cli 'example.com' --output-dir exports/`
- Tests
  - `poetry run pytest`

## Conventions & Extension Points

- DI-first: Add services/DAOs/providers in `containers.py`. Resolve via `AppContainer` (e.g., `container.services.postgres_exporter()`). Avoid `new`/direct constructors in app code.
- Parsers: Two options
  - PLY parser: subclass `parsing.parser.Parser`, implement tokens + `p_*` rules; discovery is automatic via `ParserRegistry` if `use_ply` not explicitly set to False. See `password_parser.py`, `system_parser.py`.
  - Definition parser: add a YAML to `record_definitions/` describing fields, separators, path extractors. Strategies are registered in `containers.py` (`strategies_initializer` with `RegexSeparatorChunker`, `KVHeaderExtractor`, `AliasGroupingTransformer`, `FullFileChunker`, `VaultExtractor`, etc.). See `parsing/strategies/defaults.py` and `parsing/definitions.py`.
- Parser selection: `LeakProcessor` first tries `ParserRegistry.find_best_for(path, sample_text, threshold)`, logging `parser_selection ...`, then falls back to pattern-matched PLY parser. For cookies/vaults, `LeakProcessor` enriches records with inferred `browser/profile` when missing.
- Exports & errors: Data is exported to DB by default; optional JSON via `--dump-json`. Unparsed files and parser errors are logged under `logs/`. Cookie jars from the cookie CLI are written to `exports/` using Netscape format.
- Database: DAOs in `database/dao/*`; exporter in `database/postgres.py`. Connections are pooled via container (`DatabaseContainer`). Configure via `.env` or CLI flags.

## Practical Examples

- Add a vault-like record without PLY
  - Create `record_definitions/myvault.yml` with `key: vault`, `record_separators`, and `path_extractors` for `browser/profile` if derivable.
  - Optionally adjust `Settings.prefer_definition_parsers=True` (via `.env`) to prioritize definition matching.
- Add a new PLY parser
  - Create `parsing/parsers/xyz_parser.py` subclassing `Parser`, set `pattern` to match filenames, implement lexer tokens and `p_*` grammar; add `p_error`. It will be auto-discovered by `ParserRegistry`.

## File Map (jump points)

- CLI: `stealer_parser/main.py`, helpers in `stealer_parser/helpers.py`
- DI wiring: `stealer_parser/containers.py`
- Parsing: `parsing/registry.py`, `parsing/parsers/*`, `parsing/definitions.py`, `parsing/factory.py`, `parsing/strategies/defaults.py`
- Records: `record_definitions/*.yml`
- Services: `services/leak_processor.py`, cookie CLI `cli/credential_cookie_cli.py`
- DB: `database/postgres.py`, `database/dao/*`, `database/schema.sql`

Notes
- Keep changes minimal and follow existing style. Prefer extending containers and registries over ad-hoc wiring. Log via injected `VerboseLogger`.
