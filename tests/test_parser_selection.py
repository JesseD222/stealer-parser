from pathlib import Path
import textwrap

from stealer_parser.parsing.registry import ParserRegistry
from stealer_parser.parsing.definitions import RecordDefinition, FieldDef
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory, Chunker, Extractor, Transformer
from stealer_parser.parsing.strategies.defaults import RegexSeparatorChunker, KVHeaderExtractor, AliasGroupingTransformer
from stealer_parser.helpers import init_logger


def _make_registry_with_defs(defs: list[RecordDefinition]) -> ParserRegistry:
    # Provide a simple duck-typed store with load_all()
    class _Store:
        def load_all(self):
            return defs
    store = _Store()

    strat = StrategyRegistry()
    strat.register(Chunker, RegexSeparatorChunker())
    strat.register(Extractor, KVHeaderExtractor())
    strat.register(Transformer, AliasGroupingTransformer())

    factory = ParserFactory(strat)
    logger = init_logger("test_selection", "INFO")
    return ParserRegistry(logger=logger, definition_store=store, parser_factory=factory)


def test_definition_backed_selected_over_threshold():
    defn = RecordDefinition(
        key="credential",
        file_globs=["**/passwords*.txt"],
        record_separators=[r"^-{2,}\s*$", r"^$"],
        fields=[
            FieldDef(name="username", header_patterns=[r"(?i)^username\s*[:=]"]),
            FieldDef(name="password", header_patterns=[r"(?i)^password\s*[:=]"]),
        ],
    )
    reg = _make_registry_with_defs([defn])
    sample = textwrap.dedent(
        """
        Username: alice
        Password: secret
        """
    )
    parser = reg.find_best_for(Path("/dump/system1/passwords.txt"), sample, threshold=0.1)
    assert parser is not None
    assert parser.__class__.__name__ == "ConfigurableParser"


def test_fallback_when_below_threshold():
    # Low-signal definition causing a score below threshold
    defn = RecordDefinition(
        key="credential",
        file_globs=["**/unlikely*.txt"],
        record_separators=[r"^-----$"],
        fields=[
            FieldDef(name="username", header_patterns=[r"^user:$"]),
        ],
    )
    reg = _make_registry_with_defs([defn])
    # Sample text that doesn't match
    sample = "nothing to see here"
    # Use a path that should match legacy PasswordParser by filename (contains 'password')
    parser = reg.find_best_for(Path("/dump/system1/my_password_file.txt"), sample, threshold=0.99)
    # Expect fallback to legacy parser (PasswordParser)
    assert parser is not None
    assert parser.__class__.__name__ in ("PasswordParser", "CookieParser", "SystemParser")
