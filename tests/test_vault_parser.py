import textwrap
from pathlib import Path

from stealer_parser.parsing.definition_store import DefinitionStore
from stealer_parser.parsing.factory import ParserFactory, StrategyRegistry, Chunker, Extractor, Transformer
from stealer_parser.parsing.parsers.configurable import ConfigurableParser


def test_vault_fullfile_extractor_basic():
    defs = DefinitionStore(base_dirs=[Path("record_definitions")]).load_all()
    d = next(x for x in defs if x.key == "vault")
    strategies = StrategyRegistry()
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
    # Register strategies against their interface types
    strategies.register(Chunker, RegexSeparatorChunker())
    strategies.register(Extractor, KVHeaderExtractor())
    strategies.register(Transformer, AliasGroupingTransformer())
    strategies.register(Chunker, LineChunker())
    strategies.register(Extractor, DelimitedLineExtractor())
    strategies.register(Chunker, FullFileChunker())
    strategies.register(Extractor, VaultExtractor())
    strategies.register(Transformer, VaultTransformer())

    factory = ParserFactory(strategies)

    parts = factory.build_parts(d)

    parser = ConfigurableParser(logger=None, definition=d, parts=parts)

    content = textwrap.dedent(
        """
        {"version":3,"vault":{"data":"..."}}
        """
    ).strip()

    out = parser.parse(content)
    assert out, "Should produce a record"
    rec = out[0]
    assert rec.get("type") == "vault"
    assert rec.get("vault_type") in {"metamask", "generic"}
    assert "vault_data" in rec and isinstance(rec["vault_data"], str)
