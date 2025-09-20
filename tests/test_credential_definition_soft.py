import textwrap
from pathlib import Path

from stealer_parser.parsing.definition_store import DefinitionStore
from stealer_parser.parsing.factory import ParserFactory, StrategyRegistry, Chunker, Extractor, Transformer
from stealer_parser.parsing.parsers.configurable import ConfigurableParser
from stealer_parser.parsing.strategies.defaults import RegexSeparatorChunker, KVHeaderExtractor, AliasGroupingTransformer


def test_credential_parses_soft_header():
    # Load updated credential definition
    store = DefinitionStore(base_dirs=[Path("record_definitions")])
    defs = store.load_all()
    cred = next(d for d in defs if d.key == "credential")

    # Make parser parts
    reg = StrategyRegistry()
    reg.register(Chunker, RegexSeparatorChunker())
    reg.register(Extractor, KVHeaderExtractor())
    reg.register(Transformer, AliasGroupingTransformer())
    factory = ParserFactory(reg)
    parts = factory.build_parts(cred)

    parser = ConfigurableParser(logger=None, definition=cred, parts=parts)

    sample = textwrap.dedent(
        """
        Soft: Chrome
        URL: https://example.com
        User: alice
        Pass: secret

        Soft: Firefox
        Location: https://example.org
        Login: bob
        Password: s3cr3t
        """
    ).strip()

    out = parser.parse(sample)
    assert len(out) >= 2
    r1, r2 = out[0], out[1]
    assert r1["fields"].get("soft") == "Chrome"
    assert r2["fields"].get("soft") == "Firefox"
