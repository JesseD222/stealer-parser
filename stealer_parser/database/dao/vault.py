from __future__ import annotations

from typing import Any, List

from psycopg2.pool import SimpleConnectionPool
from verboselogs import VerboseLogger

from .base import BaseDAO
from stealer_parser.models.vault import Vault


class VaultDAO(BaseDAO):
    """DAO for vault entries and artifacts."""

    def insert(self, *args: Any, conn=None) -> int:
        data: Vault = args[0]
        system_id: int = args[1]
        query = (
            """
            INSERT INTO vaults (
                system_id, vault_type, title, url, username, password, notes,
                vault_data, key_phrase, seed_words, browser, profile, filepath, stealer_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
        )
        params = (
            system_id,
            data.vault_type,
            data.title,
            data.url,
            data.username,
            data.password,
            data.notes,
            data.vault_data,
            data.key_phrase,
            data.seed_words,
            data.browser,
            data.profile,
            str(data.filepath) if data.filepath else None,
            data.stealer_name,
        )
        return self._execute_query(query, params, conn=conn)

    def bulk_insert(self, *args: Any, conn=None) -> int:
        data: List[Vault] = args[0]
        system_id: int = args[1]
        query = (
            """
            INSERT INTO vaults (
                system_id, vault_type, title, url, username, password, notes,
                vault_data, key_phrase, seed_words, browser, profile, filepath, stealer_name
            ) VALUES %s;
            """
        )
        params = [
            (
                system_id,
                v.vault_type,
                v.title,
                v.url,
                v.username,
                v.password,
                v.notes,
                v.vault_data,
                v.key_phrase,
                v.seed_words,
                v.browser,
                v.profile,
                str(v.filepath) if v.filepath else None,
                v.stealer_name,
            )
            for v in data
        ]
        return self._execute_values(query, params, conn=conn)
