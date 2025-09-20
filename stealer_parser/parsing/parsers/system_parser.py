"""Parser for system info files."""
import re
from typing import List

from stealer_parser.models import System
from stealer_parser.parsing.parser import Parser


class SystemParser(Parser):
    @property
    def pattern(self):
        return re.compile(r"(?i)(system|information|sysinfo|system_info|machine|pcinfo)")

    tokens = [
        "UID_PREFIX",
        "COMPUTER_NAME_PREFIX",
        "HWID_PREFIX",
        "USER_PREFIX",
        "IP_PREFIX",
        "COUNTRY_PREFIX",
        "DATE_PREFIX",
        "WORD",
        "NEWLINE",
    ]

    # Lexer rules
    t_ignore = " \t\r"

    def t_UID_PREFIX(self, t):
        r"[Uu][Ii][Dd]\s*:"
        return t

    def t_COMPUTER_NAME_PREFIX(self, t):
        r"[Cc]omputer\s+[Nn]ame\s*:"
        return t

    def t_HWID_PREFIX(self, t):
        r"[Hh][Ww][Ii][Dd]\s*:"
        return t

    def t_USER_PREFIX(self, t):
        r"[Uu]ser\s*:"
        return t

    def t_IP_PREFIX(self, t):
        r"[Ii][Pp]\s*:"
        return t

    def t_COUNTRY_PREFIX(self, t):
        r"[Cc]ountry\s*:"
        return t

    def t_DATE_PREFIX(self, t):
        r"(?:[Dd]ate|[Ll]og\s*[Dd]ate)\s*:"
        return t

    def t_WORD(self, t):
        r"[^\r\n]+"
        return t

    def t_NEWLINE(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)
        return t

    # Parser rules
    def p_system_info(self, p):
        """system_info : system_entry system_info
        | system_entry"""
        if len(p) == 3:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = [p[1]]

    def p_system_entry(self, p):
        """system_entry : UID_PREFIX WORD NEWLINE
        | COMPUTER_NAME_PREFIX WORD NEWLINE
        | HWID_PREFIX WORD NEWLINE
        | USER_PREFIX WORD NEWLINE
        | IP_PREFIX WORD NEWLINE
        | COUNTRY_PREFIX WORD NEWLINE
        | DATE_PREFIX WORD NEWLINE"""
        label = p[1].lower()
        value = p[2].strip()
        mapping = {
            "uid:": "machine_id",
            "computer name:": "computer_name",
            "hwid:": "hardware_id",
            "user:": "machine_user",
            "ip:": "ip_address",
            "country:": "country",
            "date:": "log_date",
            "log date:": "log_date",
        }
        key = mapping.get(label, None)
        if key:
            p[0] = {key: value}
        else:
            p[0] = {}

    def p_error(self, p):
        super().p_error(p)
