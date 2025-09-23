from __future__ import annotations

from typing import Any, List

from .base import BaseDAO
from stealer_parser.models.user_file import UserFile


class UserFilesDAO(BaseDAO):
    """DAO for general user files metadata."""

    def insert(self, *args: Any, conn=None) -> int:
        data: UserFile = args[0]
        system_id: int = args[1]
        query = (
            """
            INSERT INTO user_files (system_id, file_path, file_size, target_hits, detected_patterns, stealer_name)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
        )
        params = (
            system_id,
            data.file_path,
            data.file_size,
            data.target_hits,
            data.detected_patterns,
            data.stealer_name,
        )
        return self._execute_query(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "UserFilesDAO",
                "action": "insert",
                "table": "user_files",
                "system_id": system_id,
                "file_path": data.file_path,
                "size": data.file_size,
            },
        )

    def bulk_insert(self, *args: Any, conn=None) -> int:
        data: List[UserFile] = args[0]
        system_id: int = args[1]
        query = (
            """
            INSERT INTO user_files (system_id, file_path, file_size, target_hits, detected_patterns, stealer_name)
            VALUES %s;
            """
        )
        params = [
            (
                system_id,
                uf.file_path,
                uf.file_size,
                uf.target_hits,
                uf.detected_patterns,
                uf.stealer_name,
            )
            for uf in data
        ]
        return self._execute_values(
            query,
            params,
            conn=conn,
            ctx={
                "dao": "UserFilesDAO",
                "action": "bulk_insert",
                "table": "user_files",
                "system_id": system_id,
                "rows": len(data),
            },
        )
