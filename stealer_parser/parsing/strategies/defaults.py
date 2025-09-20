from __future__ import annotations

from typing import Iterable, Set
import re

from ..definitions import RecordDefinition
from ..factory import Chunker, Extractor, Transformer


class RegexSeparatorChunker(Chunker):
    def capabilities(self) -> Set[str]:
        return {"regex-boundary", "multiline"}

    def chunk(self, text: Iterable[str], definition: RecordDefinition) -> Iterable[list[str]]:
        seps = definition.compiled["separators"]
        buf: list[str] = []
        for ln in text:
            if seps and any(sep.search(ln) for sep in seps):
                if buf:
                    yield buf
                    buf = []
                continue
            buf.append(ln)
        if buf:
            yield buf


class KVHeaderExtractor(Extractor):
    def capabilities(self) -> Set[str]:
        return {"kv-headers"}

    def extract(self, lines: list[str], definition: RecordDefinition) -> dict:
        delims = definition.compiled["delims"]
        headers = definition.compiled["headers"]
        data: dict = {}
        for ln in lines:
            if any(h.search(ln) for h in headers):
                key = None
                val = None
                for d in delims:
                    m = d.search(ln)
                    if m:
                        key = ln[: m.start()].strip()
                        val = ln[m.end() :].strip()
                        break
                if key is not None:
                    data.setdefault("_order", []).append(key)
                    data[key] = val
        return data


class AliasGroupingTransformer(Transformer):
    def capabilities(self) -> Set[str]:
        return {"grouping", "kv-headers"}

    def transform(self, raw: dict, definition: RecordDefinition) -> dict:
        if not raw:
            return {}
        result: dict = {"type": definition.key, "fields": {}, "groups": {}}
        field_map = {f.name: f for f in definition.fields}
        for fname, fdef in field_map.items():
            candidates = [a.lower() for a in ([fname] + fdef.aliases)]
            match = next(
                (k for k in raw.keys() if isinstance(k, str) and k.lower() in candidates),
                None,
            )
            if match:
                result["fields"][fname] = raw.get(match)
                if fdef.group:
                    result["groups"].setdefault(fdef.group, {})[fname] = raw.get(match)
        return result
