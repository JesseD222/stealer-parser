"""Parser for cookie files."""
import re
from typing import List

from stealer_parser.models import Cookie
from stealer_parser.parsing.parser import Parser


class CookieParser(Parser):
    use_ply = False
    @property
    def pattern(self):
        return re.compile(r"(?i)cookie")

    def parse(self, text: str, **kwargs) -> List[Cookie]:
        cookies = []
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 7:
                # Fallback: split on whitespace into 7 chunks max
                import re as _re
                parts = _re.split(r"\s+", line, maxsplit=6)
                if len(parts) != 7:
                    continue
            cookies.append(
                Cookie(
                    domain=parts[0],
                    domain_specified=parts[1],
                    path=parts[2],
                    secure=parts[3],
                    expiry=parts[4],
                    name=parts[5],
                    value=parts[6],
                    browser=kwargs.get("browser", "unknown"),
                    profile=kwargs.get("profile", "unknown"),
                    filepath=kwargs.get("filename", "unknown"),
                )
            )
        return cookies
