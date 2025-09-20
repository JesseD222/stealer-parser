from __future__ import annotations

from functools import cached_property
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
import re


class FieldDef(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    header_patterns: List[str] = Field(default_factory=list)
    value_patterns: List[str] = Field(default_factory=list)
    group: Optional[str] = None
    required: bool = False
    order_hint: Optional[int] = None


class RecordDefinition(BaseModel):
    key: str
    description: Optional[str] = None
    file_globs: List[str] = Field(default_factory=list)
    record_separators: List[str] = Field(default_factory=list)
    kv_delimiters: List[str] = Field(default_factory=lambda: [":", "="])
    multiline: bool = True
    groups: Dict[str, List[str]] = Field(default_factory=dict)
    fields: List[FieldDef] = Field(default_factory=list)
    score_weights: Dict[str, float] = Field(
        default_factory=lambda: {"header": 2.0, "separator": 1.0, "alias": 0.5, "path": 1.0}
    )

    @cached_property
    def compiled(self) -> Dict[str, List[re.Pattern]]:
        headers = [re.compile(pat, re.I) for f in self.fields for pat in f.header_patterns]
        seps = [re.compile(pat, re.I) for pat in self.record_separators]
        aliases = [re.compile(re.escape(a), re.I) for f in self.fields for a in f.aliases]
        delims = [re.compile(rf"\s*{re.escape(d)}\s*") for d in self.kv_delimiters]
        return {"headers": headers, "separators": seps, "aliases": aliases, "delims": delims}

    def capabilities(self) -> Set[str]:
        caps: Set[str] = set()
        if self.record_separators:
            caps.add("regex-boundary")
        if any(f.header_patterns for f in self.fields):
            caps.add("kv-headers")
        if self.multiline:
            caps.add("multiline")
        if self.groups:
            caps.add("grouping")
        return caps
