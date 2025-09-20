incremental roadmap to integrate the dynamic, definition-driven parser approach while phasing out PLY and keeping DI, Registry, and services intact.

Milestone 0 — Foundations and safety rails
- Add feature flag to prefer “definition-backed” parsers over legacy PLY (env/CLI).
- Introduce settings for record definition directories, confidence threshold, and fallback behavior.
- Add basic telemetry fields: parser_kind, definition_key, match_score to logs.

Milestone 1 — Unified record definitions and discovery
- Model a RecordDefinition (fields, aliases, header patterns, separators, grouping, delimiters).
- Implement a DefinitionStore that loads YAML/JSON from configured dirs.
- Create a fast matcher that scores a file sample against definitions (path globs + content patterns).
- Add unit tests with synthetic samples per record type; tune default scoring weights and threshold.

Milestone 2 — Strategy registry and abstract factory
- Introduce a StrategyRegistry with capability tags (e.g., regex-boundary, kv-headers, multiline, grouping).
- Implement a ParserFactory that picks strategies based on definition capabilities (no if/else).
- Register minimal strategies: RegexSeparatorChunker, KVHeaderExtractor, AliasGroupingTransformer.
- Wire these into AppContainer via dependency-injector (singletons with cached registration).

Milestone 3 — Configurable parser and registry integration
- Implement ConfigurableParser that conforms to stealer_parser.parsing.parser.Parser.
- Extend ParserRegistry with find_best_for(path, sample_text): pick definition-backed parser when score ≥ threshold; else fallback to legacy.
- Modify LeakProcessor to sample input (first 8–12KB) and use find_best_for. Keep legacy flow unchanged otherwise.
- Add golden tests to ensure outputs match current PLY outputs on known fixtures (credential, cookie).

Milestone 4 — Tokenizer and richer extraction
- Replace simple line-splitting with a streaming regex token generator (labels, values, separators).
- Preserve record atomicity: chunk at record boundaries; keep field order within a record.
- Add validation hooks in Transform: structural pattern matching on aliases/groups to normalize to models.

Milestone 5 — Coverage expansion and robustness
- Add definitions for additional record types (system info, autofill, vault).
- Add per-definition value validators (e.g., URL, email, password heuristics).
- Handle messy inputs: mixed encodings, very long lines, empty sections, nested separators.
- Introduce a “confidence downgrade” path: if transform yields insufficient required fields, demote to legacy parser (guard-rail).

Milestone 6 — Observability and quality gates
- Add metrics: match_rate, avg_match_score, parse_latency, records_per_file; per parser_kind and definition_key.
- Add DLQ/side-channel for low-confidence or failed normalizations; persist input excerpts for triage.
- Linters and CI gates: run pytest, basic performance smoke (parse N fixtures under T seconds).

Milestone 7 — Migration and deprecation plan
- Run in dual mode by default; log match decisions and result diffs for a sample period.
- Promote definition-backed parsers per record type once parity is proven; switch default flag.
- Mark unused PLY parsers deprecated; remove after a grace period.

Optional Milestone 8 — Async pipeline and broker (future)
- Start with in-process asyncio queues between stages (Inspector → Chunker → Extractor → Transformer → Loader).
- Abstract transports; later swap to FastStream Redis broker for distributed workers.
- Keep record as the atomic unit; partition by DataUnit; add DLQ per stage.

Deliverables per milestone
- Code: models, registry/factory, strategies, parser, and DI wiring.
- Tests: unit tests for matcher and strategies; golden tests for output parity; stress tests for large files.
- Docs: definition schema, authoring guide, examples; migration notes and feature flag usage.
- Observability: log fields and basic metrics integrated with existing VerboseLogger.

Key risks and mitigations
- Ambiguous matches: use conservative thresholds, path-glob signals, and required-field validation.
- Mixed record types in one file: allow multi-definition parsing with record-level scoring if needed later.
- Performance: compile regexes once per definition; sample only a small prefix; stream tokenization.
- Backward compatibility: always maintain legacy fallback behind flag; add differential tests.

Setup tasks
- Add settings to config.py for definitions_dir, score_threshold, prefer_definition_parsers.
- Update AppContainer to register DefinitionStore, StrategyRegistry, ParserFactory, and to pass them into ParserRegistry.
- Create a record_definitions/ directory with initial credential.yml and cookie.yml.

Acceptance criteria for initial rollout
- ≥95% match rate on curated samples with parity to PLY outputs for credential and cookie.
- No regressions in end-to-end CLI workflow; LeakProcessor unchanged for non-matching files.
- Clear logs showing parser selection and confidence.

If you want, I can scaffold the minimal models, registry wiring, and one initial RecordDefinition plus tests as the first PR.

JesseD222: yes do that

GitHub Copilot: Great. Here’s a minimal, incremental scaffold to introduce definition-driven, dynamically configured parsers while keeping legacy PLY parsers intact. It includes new models, a matcher, strategy registry, a configurable parser, DI wiring, a sample definition, and tests. You can drop these in as a first PR and iterate.

Code additions

````python
from __future__ import annotations

from functools import cached_property
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
import re


class FieldDef(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    header_patterns: List[str] = Field(default_factory=list)  # regexes to detect label lines
    value_patterns: List[str] = Field(default_factory=list)   # optional value validation
    group: Optional[str] = None
    required: bool = False
    order_hint: Optional[int] = None


class RecordDefinition(BaseModel):
    key: str                                      # e.g. "credential", "cookie"
    description: Optional[str] = None
    file_globs: List[str] = Field(default_factory=list)        # path globs
    record_separators: List[str] = Field(default_factory=list) # regex boundaries between records
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
````

````python
from __future__ import annotations

from pathlib import Path
from typing import List
from pydantic import BaseModel
import json
import yaml

from .definitions import RecordDefinition


class DefinitionStore(BaseModel):
    base_dirs: List[Path]

    class Config:
        arbitrary_types_allowed = True

    def load_all(self) -> List[RecordDefinition]:
        defs: List[RecordDefinition] = []
        for base in self.base_dirs:
            if not base.exists():
                continue
            for p in base.rglob("*.yml"):
                defs.append(RecordDefinition.model_validate(yaml.safe_load(p.read_text())))
            for p in base.rglob("*.yaml"):
                defs.append(RecordDefinition.model_validate(yaml.safe_load(p.read_text())))
            for p in base.rglob("*.json"):
                defs.append(RecordDefinition.model_validate(json.loads(p.read_text())))
        return defs
````

````python
from __future__ import annotations

from pathlib import Path
from typing import Iterable
import fnmatch

from .definitions import RecordDefinition


def score_definition(
    path: Path, sample_lines: Iterable[str], definition: RecordDefinition
) -> float:
    lines = list(sample_lines)
    weights = definition.score_weights
    score = 0.0

    # path-based signal
    if any(fnmatch.fnmatch(str(path), pat) for pat in definition.file_globs):
        score += weights.get("path", 1.0)

    # content-based signals
    sep_hits = sum(
        1 for ln in lines for sep in definition.compiled["separators"] if sep.search(ln)
    )
    hdr_hits = sum(
        1 for ln in lines for hdr in definition.compiled["headers"] if hdr.search(ln)
    )
    alias_hits = sum(
        1 for ln in lines for al in definition.compiled["aliases"] if al.search(ln)
    )

    score += sep_hits * weights.get("separator", 1.0)
    score += hdr_hits * weights.get("header", 2.0)
    score += alias_hits * weights.get("alias", 0.5)

    denom = max(10, len(lines))
    return score / denom
````

````python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, List, Protocol, Set, Tuple, Type, TypeVar, Generic

from .definitions import RecordDefinition

S = TypeVar("S", bound="Strategy")


class Strategy(ABC):
    @abstractmethod
    def capabilities(self) -> Set[str]: ...


class Chunker(Strategy, ABC):
    @abstractmethod
    def chunk(self, text: Iterable[str], definition: RecordDefinition) -> Iterable[list[str]]: ...


class Extractor(Strategy, ABC):
    @abstractmethod
    def extract(self, lines: list[str], definition: RecordDefinition) -> dict: ...


class Transformer(Strategy, ABC):
    @abstractmethod
    def transform(self, raw: dict, definition: RecordDefinition) -> dict: ...


class StrategyRegistry:
    def __init__(self) -> None:
        self._impls: Dict[Type[Strategy], list[Tuple[Set[str], Strategy]]] = {}

    def register(self, iface: Type[S], impl: S) -> None:
        caps = impl.capabilities()
        self._impls.setdefault(iface, []).append((caps, impl))

    def best_for(self, iface: Type[S], requirements: Set[str]) -> S:
        candidates = self._impls.get(iface, [])
        if not candidates:
            raise LookupError(f"No strategies registered for {iface.__name__}")
        # choose maximal intersection; first-registered wins ties
        best = max(candidates, key=lambda c: len(requirements & c[0]))
        return best[1]  # type: ignore[return-value]


@dataclass
class ParserParts:
    chunker: Chunker
    extractor: Extractor
    transformer: Transformer


class ParserFactory:
    def __init__(self, strategies: StrategyRegistry) -> None:
        self._strategies = strategies

    def build_parts(self, definition: RecordDefinition) -> ParserParts:
        req = definition.capabilities()
        return ParserParts(
            chunker=self._strategies.best_for(Chunker, req),
            extractor=self._strategies.best_for(Extractor, req),
            transformer=self._strategies.best_for(Transformer, req),
        )
````

````python
from __future__ import annotations

from typing import Iterator

from stealer_parser.parsing.parser import Parser  # existing base
from stealer_parser.parsing.definitions import RecordDefinition
from stealer_parser.parsing.factory import ParserParts


class ConfigurableParser(Parser):
    """
    A high-level parser dynamically configured per RecordDefinition.
    It avoids PLY by chunking + extracting + transforming based on strategies.
    """

    name = "configurable"

    def __init__(self, definition: RecordDefinition, parts: ParserParts) -> None:
        super().__init__()
        self.definition = definition
        self.parts = parts

    def parse_text(self, text: str) -> Iterator[dict]:
        lines = text.splitlines()
        for chunk in self.parts.chunker.chunk(lines, self.definition):
            raw = self.parts.extractor.extract(chunk, self.definition)
            record = self.parts.transformer.transform(raw, self.definition)
            if record:
                yield record
````

````python
from __future__ import annotations

from typing import Iterable, Set
from collections import defaultdict

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
                # split on first matching delimiter
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
````

Patches to existing files

````python
# ...existing code...
from pathlib import Path
from typing import Optional

from .definition_store import DefinitionStore
from .matcher import score_definition
from .factory import ParserFactory
from .parsers.configurable import ConfigurableParser

DEFAULT_THRESHOLD = 0.15  # can be overridden by settings

class ParserRegistry:
    # ...existing code...

    def __init__(self, *args, definition_store: Optional[DefinitionStore] = None, parser_factory: Optional[ParserFactory] = None, **kwargs):
        # ...existing code...
        self._definition_store = definition_store
        self._parser_factory = parser_factory
        # ...existing code...

    def find_best_for(self, path: Path, sample_text: str, threshold: float = DEFAULT_THRESHOLD):
        """
        Returns a configured ConfigurableParser when a definition matches with sufficient confidence,
        otherwise falls back to the legacy resolution.
        """
        # Legacy behavior if not wired
        if not (self._definition_store and self._parser_factory):
            return self.get_for_path(path)  # ...existing code...

        defs = self._definition_store.load_all()
        if not defs:
            return self.get_for_path(path)  # ...existing code...

        lines = sample_text.splitlines()[:200]
        scored = [(d, score_definition(path, lines, d)) for d in defs]
        scored.sort(key=lambda x: x[1], reverse=True)

        if scored and scored[0][1] >= threshold:
            best_def = scored[0][0]
            parts = self._parser_factory.build_parts(best_def)
            return ConfigurableParser(best_def, parts)

        return self.get_for_path(path)  # ...existing code...
```

````python
// filepath: containers.py
# ...existing code...
from pathlib import Path
from dependency_injector import containers, providers

# New imports
from stealer_parser.parsing.definition_store import DefinitionStore
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
)
from stealer_parser.parsing.registry import ParserRegistry

class AppContainer(containers.DeclarativeContainer):
    # ...existing code...

    # Settings provider should already exist; assume `config` provides access to settings.
    # For example: config().record_definitions_dirs, config().parser_match_threshold, etc.

    record_def_dirs = providers.List(
        providers.Callable(lambda cfg: [Path(p) for p in cfg.record_definitions_dirs], config),
    )

    definition_store = providers.Singleton(
        DefinitionStore, base_dirs=record_def_dirs
    )

    strategy_registry = providers.Singleton(StrategyRegistry)
    parser_factory = providers.Singleton(ParserFactory, strategies=strategy_registry)

    # Register default strategies once
    _register_strategies = providers.Callable(
        lambda reg: (
            reg.register(RegexSeparatorChunker.__bases__[0], RegexSeparatorChunker()),  # Chunker iface inferred
            reg.register(KVHeaderExtractor.__bases__[0], KVHeaderExtractor()),          # Extractor
            reg.register(AliasGroupingTransformer.__bases__[0], AliasGroupingTransformer()),  # Transformer
        ),
        strategy_registry,
    )

    parser_registry = providers.Singleton(
        ParserRegistry,
        definition_store=definition_store,
        parser_factory=parser_factory,
    )
```

````python
// filepath: stealer_parser/config.py
# ...existing code...
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # ...existing code...
    # New feature flags and configuration
    prefer_definition_parsers: bool = False
    record_definitions_dirs: List[str] = ["record_definitions"]
    parser_match_threshold: float = 0.15

    model_config = SettingsConfigDict(env_prefix="STEALER_", env_file=".env", env_nested_delimiter="__")

# ...existing code...
```

````python
// filepath: stealer_parser/services/leak_processor.py
# ...existing code...
from pathlib import Path
from dependency_injector.wiring import inject, Provide

from stealer_parser.parsing.registry import ParserRegistry
from stealer_parser.config import Settings

class LeakProcessor:
    # ...existing code...

    @inject
    def __init__(self, parser_registry: ParserRegistry = Provide["parser_registry"], settings: Settings = Provide["config"]) -> None:
        # ...existing code...
        self.parser_registry = parser_registry
        self.settings = settings
        # ...existing code...

    def _sample_text(self, fileobj, limit: int = 12_000) -> str:
        pos = fileobj.tell()
        data = fileobj.read(limit)
        try:
            if isinstance(data, (bytes, bytearray)):
                text = data.decode("utf-8", errors="ignore")
            else:
                text = str(data)
        finally:
            fileobj.seek(pos)
        return text

    def _select_parser(self, path: Path, fileobj):
        # Prefer definition-backed parsers when enabled, else legacy selection
        if getattr(self.settings, "prefer_definition_parsers", False):
            sample = self._sample_text(fileobj)
            return self.parser_registry.find_best_for(path, sample, threshold=self.settings.parser_match_threshold)
        return self.parser_registry.get_for_path(path)  # ...existing code...

    def process_file(self, path: Path, fileobj):
        # ...existing code...
        parser = self._select_parser(path, fileobj)
        text = fileobj.read().decode("utf-8", errors="ignore")
        for record in parser.parse_text(text):
            # ...existing persistence/export...
            pass
```

Sample definition

````yaml
// filepath: record_definitions/credential.yml
key: credential
description: Simple key/value credential records
file_globs: ["**/credentials*.txt", "**/passwords*.txt", "**/logins*.txt"]
record_separators:
  - "^-{2,}\\s*$"
  - "^$"
kv_delimiters: [":", "="]
multiline: true
fields:
  - name: url
    aliases: ["site", "origin", "host"]
    header_patterns: ["(?i)^(url|site|origin|host)\\s*[:=]"]
    required: true
  - name: username
    aliases: ["login", "user", "email"]
    header_patterns: ["(?i)^(username|login|user|email)\\s*[:=]"]
  - name: password
    aliases: ["pass", "pwd"]
    header_patterns: ["(?i)^(password|pass|pwd)\\s*[:=]"]
groups:
  auth: ["username", "password"]
```

Tests

````python
// filepath: tests/test_definition_matching.py
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
````

````python
// filepath: tests/test_configurable_parser.py
import textwrap
from stealer_parser.parsing.definitions import RecordDefinition, FieldDef
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory
from stealer_parser.parsing.parsers.configurable import ConfigurableParser
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
)

def make_parser(defn: RecordDefinition) -> ConfigurableParser:
    reg = StrategyRegistry()
    reg.register(type(RegexSeparatorChunker()), RegexSeparatorChunker())  # type: ignore[arg-type]
    reg.register(type(KVHeaderExtractor()), KVHeaderExtractor())          # type: ignore[arg-type]
    reg.register(type(AliasGroupingTransformer()), AliasGroupingTransformer())  # type: ignore[arg-type]
    factory = ParserFactory(reg)
    parts = factory.build_parts(defn)
    return ConfigurableParser(defn, parts)

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
    parser = make_parser(defn)
    records = list(parser.parse_text(text))
    assert len(records) == 2
    assert records[0]["fields"]["username"] == "alice"
    assert records[0]["groups"]["auth"]["password"] == "secret"
    assert records[1]["fields"]["url"].endswith("example.org")
````

How to wire and run

- Register the new providers in AppContainer (containers.py patch above).
- Expose settings via environment variables if desired:
  - STEALER_PREFER_DEFINITION_PARSERS=true
  - STEALER_RECORD_DEFINITIONS_DIRS='["record_definitions"]'
  - STEALER_PARSER_MATCH_THRESHOLD=0.15
- Run tests:
  - poetry install
  - poetry run pytest -q

Next steps

- Add definitions for cookie/system info and adjust threshold using real samples.
- Expand strategies (e.g., table-like extractors) and register them via StrategyRegistry without changing selection logic.
- Once parity is proven, flip prefer_definition_parsers to true by default.Tests

````python
// filepath: tests/test_definition_matching.py
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
````

````python
// filepath: tests/test_configurable_parser.py
import textwrap
from stealer_parser.parsing.definitions import RecordDefinition, FieldDef
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory
from stealer_parser.parsing.parsers.configurable import ConfigurableParser
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
)

def make_parser(defn: RecordDefinition) -> ConfigurableParser:
    reg = StrategyRegistry()
    reg.register(type(RegexSeparatorChunker()), RegexSeparatorChunker())  # type: ignore[arg-type]
    reg.register(type(KVHeaderExtractor()), KVHeaderExtractor())          # type: ignore[arg-type]
    reg.register(type(AliasGroupingTransformer()), AliasGroupingTransformer())  # type: ignore[arg-type]
    factory = ParserFactory(reg)
    parts = factory.build_parts(defn)
    return ConfigurableParser(defn, parts)

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
    parser = make_parser(defn)
    records = list(parser.parse_text(text))
    assert len(records) == 2
    assert records[0]["fields"]["username"] == "alice"
    assert records[0]["groups"]["auth"]["password"] == "secret"
    assert records[1]["fields"]["url"].endswith("example.org")
````

How to wire and run

- Register the new providers in AppContainer (containers.py patch above).
- Expose settings via environment variables if desired:
  - STEALER_PREFER_DEFINITION_PARSERS=true
  - STEALER_RECORD_DEFINITIONS_DIRS='["record_definitions"]'
  - STEALER_PARSER_MATCH_THRESHOLD=0.15
- Run tests:
  - poetry install
  - poetry run pytest -q

Next steps

- Add definitions for cookie/system info and adjust threshold using real samples.
- Expand strategies (e.g., table-like extractors) and register them via StrategyRegistry without changing selection logic.
- Once parity is proven, flip prefer_definition_parsers to true by default.
