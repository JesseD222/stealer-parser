"""Base parser class integrating PLY for lexing and parsing."""
from abc import ABC, abstractmethod
from typing import Any, List, Pattern

from stealer_parser.ply.src.ply import lex, yacc
from typing import Any as _Any
from verboselogs import VerboseLogger


class Parser(ABC):
    """
    Abstract base class for a file parser that uses PLY for lexing and parsing.
    """

    tokens: list[str] = []
    use_ply: bool = True

    def __init__(self, logger: VerboseLogger):
        self._logger = logger
        self.lexer = None
        self.parser = None

    @property
    @abstractmethod
    def pattern(self) -> Pattern[str]:
        """Regex pattern to match files this parser can handle."""
        raise NotImplementedError

    def build(self, **kwargs: Any) -> None:
        """Build the lexer and parser if using PLY."""
        if not self.use_ply:
            return
        self.lexer = lex.lex(module=self, **kwargs)
        self.parser = yacc.yacc(module=self, **kwargs)

    def parse(self, text: str) -> List[Any]:
        """Default parse using PLY if enabled; override in subclasses as needed."""
        if self.use_ply:
            if not self.lexer or not self.parser:
                raise RuntimeError("Parser not built. Call build() before parsing.")
            result = self.parser.parse(text, lexer=self.lexer)
            return result if result is not None else []
        return []

    def t_error(self, t: _Any) -> None:
        """Lexer error handling rule."""
        try:
            self._logger.debug(f"Illegal character '{t.value[0]}' at line {t.lineno}")
            t.lexer.skip(1)
        except Exception:
            self._logger.debug("Lexer error encountered; skipping 1 char.")
            try:
                t.lexer.skip(1)
            except Exception:
                pass

    def p_error(self, p: _Any) -> None:
        """Parser error handling rule."""
        if p:
            try:
                self._logger.debug(
                    f"Syntax error at token '{getattr(p, 'type', '?')}' with value '{getattr(p, 'value', '?')}' at line {getattr(p, 'lineno', '?')}"
                )
            except Exception:
                self._logger.debug("Syntax error in parser.")
        else:
            self._logger.debug("Syntax error at EOF")

    # Common lexer rules can be defined here
    def t_newline(self, t: _Any) -> _Any:
        r"\n+"
        try:
            t.lexer.lineno += len(t.value)
        except Exception:
            pass
        return t
