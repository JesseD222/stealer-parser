import textwrap

from stealer_parser.parsing.definitions import RecordDefinition, FieldDef
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory, Chunker, Extractor, Transformer
from stealer_parser.parsing.parsers.configurable import ConfigurableParser
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
)


def _make_parser(defn: RecordDefinition) -> ConfigurableParser:
    reg = StrategyRegistry()
    reg.register(Chunker, RegexSeparatorChunker())
    reg.register(Extractor, KVHeaderExtractor())
    reg.register(Transformer, AliasGroupingTransformer())
    factory = ParserFactory(reg)
    parts = factory.build_parts(defn)
    # Provide dummy logger via None; Parser ignores when use_ply=False
    from stealer_parser.helpers import init_logger
    parser = ConfigurableParser(logger=init_logger("test", "INFO"), definition=defn, parts=parts)
    return parser


def test_configurable_parser_credential():
    defn = RecordDefinition(
        key="credential",
        record_separators=[r"^-{2,}\s*$", r"^$"],
        fields=[
            FieldDef(name="username", aliases=["user", "login"], header_patterns=[r"(?i)^(username|user|login)\s*[:=]"], group="auth"),
            FieldDef(name="password", aliases=["pass", "pwd"], header_patterns=[r"(?i)^(password|pass|pwd)\s*[:=]"], group="auth"),
            FieldDef(name="url", aliases=["site"], header_patterns=[r"(?i)^(url|site)\s*[:=]"]),
        ],
    )
    text = textwrap.dedent(
        """
        URL: https://example.com
        Username: alice
        Password: secret

        --
        Site: https://example.org
        Login: bob
        Pass: hunter2
        """
    ).strip()
    parser = _make_parser(defn)
    records = parser.parse(text)
    assert len(records) == 2
    assert records[0]["fields"]["username"] == "alice"
    assert records[0]["groups"]["auth"]["password"] == "secret"
    assert records[1]["fields"]["url"].endswith("example.org")
