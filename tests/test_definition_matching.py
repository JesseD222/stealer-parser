import textwrap
from pathlib import Path

from stealer_parser.parsing.definitions import RecordDefinition, FieldDef
from stealer_parser.parsing.matcher import score_definition


def test_score_definition_simple():
    defn = RecordDefinition(
        key="credential",
        file_globs=["**/credentials*.txt"],
        record_separators=[r"^-{2,}\s*$", r"^$"],
        fields=[
            FieldDef(name="username", header_patterns=[r"(?i)^username\s*[:=]"]),
            FieldDef(name="password", header_patterns=[r"(?i)^password\s*[:=]"]),
        ],
    )
    sample = textwrap.dedent(
        """
        Username: alice
        Password: secret
        --
        Username: bob
        Password: hunter2
        """
    ).strip().splitlines()
    score = score_definition(Path("/tmp/credentials_1.txt"), sample, defn)
    assert score > 0.15
