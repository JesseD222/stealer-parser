from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile

from stealer_parser.models.archive_wrapper import ArchiveWrapper
from stealer_parser.services.leak_processor import LeakProcessor
from stealer_parser.parsing.registry import ParserRegistry
from stealer_parser.parsing.definition_store import DefinitionStore
from stealer_parser.parsing.factory import ParserFactory, StrategyRegistry
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
    LineChunker,
    DelimitedLineExtractor,
    FullFileChunker,
    VaultExtractor,
    VaultTransformer,
)
from verboselogs import VerboseLogger


def build_registry(logger: VerboseLogger) -> ParserRegistry:
    defs = DefinitionStore(base_dirs=[Path("record_definitions")])
    strategies = StrategyRegistry()
    strategies.register(type(RegexSeparatorChunker()), RegexSeparatorChunker())
    strategies.register(type(KVHeaderExtractor()), KVHeaderExtractor())
    strategies.register(type(AliasGroupingTransformer()), AliasGroupingTransformer())
    strategies.register(type(LineChunker()), LineChunker())
    strategies.register(type(DelimitedLineExtractor()), DelimitedLineExtractor())
    strategies.register(type(FullFileChunker()), FullFileChunker())
    strategies.register(type(VaultExtractor()), VaultExtractor())
    strategies.register(type(VaultTransformer()), VaultTransformer())
    factory = ParserFactory(strategies)
    return ParserRegistry(logger=logger, definition_store=defs, parser_factory=factory)


def main():
    archive_path = Path("data/testleak.zip")
    if not archive_path.exists():
        print("Archive not found: data/testleak.zip", file=sys.stderr)
        sys.exit(1)

    logger = VerboseLogger(__name__)
    registry = build_registry(logger)
    with ZipFile(str(archive_path)) as zf:
        wrapper = ArchiveWrapper(zf)
        processor = LeakProcessor(parser_registry=registry, logger=logger)
        leak = processor.process_leak(wrapper)

    # Summarize
    cookie_counts = {}
    vault_counts = {}
    for sysdata in leak.systems:
        for c in sysdata.cookies:
            key = (c.browser or "unknown", c.profile or "unknown")
            cookie_counts[key] = cookie_counts.get(key, 0) + 1
        for v in sysdata.vaults:
            key = (v.browser or "unknown", v.profile or "unknown")
            vault_counts[key] = vault_counts.get(key, 0) + 1

    print("Cookies by (browser, profile):")
    for k, v in sorted(cookie_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k[0]} / {k[1]}: {v}")

    print("\nVaults by (browser, profile):")
    for k, v in sorted(vault_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k[0]} / {k[1]}: {v}")


if __name__ == "__main__":
    main()
