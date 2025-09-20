from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple, Type, TypeVar

from .definitions import RecordDefinition


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


S = TypeVar("S", bound=Strategy)


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
