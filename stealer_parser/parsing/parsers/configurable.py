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
        filename = kwargs.get("filename")
        for chunk in self.parts.chunker.chunk(lines, self.definition):
            raw = self.parts.extractor.extract(chunk, self.definition)
            record = self.parts.transformer.transform(raw, self.definition)
            if record:
                # Apply path extractors if filename present
                if filename:
                    for rx in self.definition.compiled.get("path_extractors", []):
                        m = rx.search(filename)
                        if m:
                            gd = m.groupdict()
                            # Merge only known fields onto the record's top-level
                            for k, v in gd.items():
                                if v is None:
                                    continue
                                if k in ("browser", "profile"):
                                    record[k] = v
                records.append(record)
        return records
