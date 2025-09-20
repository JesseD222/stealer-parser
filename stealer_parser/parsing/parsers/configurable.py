from __future__ import annotations

from typing import Iterator

from stealer_parser.parsing.parser import Parser
from stealer_parser.parsing.definitions import RecordDefinition
from stealer_parser.parsing.factory import ParserParts


class ConfigurableParser(Parser):
    """
    A high-level parser dynamically configured per RecordDefinition.
    It avoids PLY by chunking + extracting + transforming based on strategies.
    """

    use_ply = False

    def __init__(self, logger, definition: RecordDefinition, parts: ParserParts):
        super().__init__(logger=logger)
        self.definition = definition
        self.parts = parts

    @property
    def pattern(self):
        # Match anything; selection is performed by registry before instantiation.
        import re

        return re.compile(r".*")

    def parse(self, text: str, **kwargs) -> list[dict]:
        records: list[dict] = []
        lines = text.splitlines()
        for chunk in self.parts.chunker.chunk(lines, self.definition):
            raw = self.parts.extractor.extract(chunk, self.definition)
            record = self.parts.transformer.transform(raw, self.definition)
            if record:
                records.append(record)
        return records
