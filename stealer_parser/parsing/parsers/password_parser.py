"""Parser for password files."""
import re
from typing import List

from stealer_parser.models import Credential
from stealer_parser.parsing.parser import Parser


class PasswordParser(Parser):
    @property
    def pattern(self):
        return re.compile(r"(?i)password")
    tokens = [
        "SOFT_PREFIX",
        "HOST_PREFIX",
        "USER_PREFIX",
        "PASSWORD_PREFIX",
        "WORD",
        "NEWLINE",
    ]

    # Lexer rules
    t_ignore = " \t\r"

    def t_SOFT_PREFIX(self, t):
        r"[Ss][Oo][Ff][Tt]\s*:"
        return t

    def t_HOST_PREFIX(self, t):
        r"(?:[Hh][Oo][Ss][Tt]|[Uu][Rr][Ll])\s*:"
        return t

    def t_USER_PREFIX(self, t):
        r"(?:[Ll][Oo][Gg][Ii][Nn]|[Uu][Ss][Ee][Rr])\s*:"
        return t

    def t_PASSWORD_PREFIX(self, t):
        r"(?:[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss]|[Pp][Ww][Dd])\s*:"
        return t

    def t_WORD(self, t):
        r"[^\r\n]+"
        return t

    def t_NEWLINE(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)
        return t

    # Parser rules
    def p_credentials(self, p):
        """credentials : credential credentials
        | credential"""
        if len(p) == 3:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = [p[1]]

    def p_credential(self, p):
        """credential : SOFT_PREFIX WORD NEWLINE HOST_PREFIX WORD NEWLINE USER_PREFIX WORD NEWLINE PASSWORD_PREFIX WORD NEWLINE"""
        p[0] = Credential(
            software=p[2], host=p[5], username=p[8], password=p[11]
        )

    def p_error(self, p):
        super().p_error(p)
