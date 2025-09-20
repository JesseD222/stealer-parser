"""Parser plugin system for handling different file types."""
import inspect
import pkgutil
from pathlib import Path
from typing import List, Optional

from verboselogs import VerboseLogger

from . import parsers
from .parser import Parser
from .definition_store import DefinitionStore
from .matcher import score_definition
from .parsers.configurable import ConfigurableParser
from .factory import ParserFactory


class ParserRegistry:
    """Registry for file parser plugins."""

    def __init__(self, logger: VerboseLogger, definition_store: Optional[DefinitionStore] = None, parser_factory: Optional[ParserFactory] = None):
        self.logger = logger
        self._parsers = self._discover_parsers()
        self._definition_store = definition_store
        self._parser_factory = parser_factory

    def _discover_parsers(self) -> List[Parser]:
        """Discover all parser classes in the 'parsers' module."""
        discovered_parsers = []
        for _, name, _ in pkgutil.iter_modules(parsers.__path__):
            module = __import__(f"{parsers.__name__}.{name}", fromlist=[""])
            for member in inspect.getmembers(module, inspect.isclass):
                if issubclass(member[1], Parser) and member[1] is not Parser:
                    cls = member[1]
                    # Skip classes explicitly marked as non-discoverable
                    if getattr(cls, "use_ply", True) is False and cls.__name__.lower().startswith("configurable"):
                        continue
                    try:
                        parser_instance = cls(logger=self.logger)
                        parser_instance.build()
                        discovered_parsers.append(parser_instance)
                    except TypeError:
                        # Constructor signature not compatible with discovery; skip.
                        continue
        return discovered_parsers

    def get_parser(self, filename: str) -> Optional[Parser]:
        """
        Find the first parser that matches the filename.
        """
        for parser in self._parsers:
            if parser.pattern.search(filename):
                return parser
        return None

    def find_best_for(self, path: Path, sample_text: str, threshold: float = 0.15) -> Optional[Parser]:
        """Return a configured definition-backed parser if a confident match is found; otherwise fallback."""
        if not (self._definition_store and self._parser_factory):
            return self.get_parser(str(path))

        defs = self._definition_store.load_all()
        if not defs:
            return self.get_parser(str(path))

        lines = sample_text.splitlines()[:200]
        scored = [(d, score_definition(path, lines, d)) for d in defs]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] >= threshold:
            best_def = scored[0][0]
            parts = self._parser_factory.build_parts(best_def)
            # Pass logger from registry to the configurable parser
            return ConfigurableParser(logger=self.logger, definition=best_def, parts=parts)

        return self.get_parser(str(path))
