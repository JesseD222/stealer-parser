"""Data model to define general user files found in leaks."""
from dataclasses import dataclass
from .types import StealerNameType


@dataclass
class UserFile:
    """Class defining a general user file record with simple metadata."""

    file_path: str
    file_size: int | None = None
    target_hits: int | None = None
    detected_patterns: str | None = None
    stealer_name: StealerNameType | None = None
