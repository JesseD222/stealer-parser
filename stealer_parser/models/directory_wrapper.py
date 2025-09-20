from __future__ import annotations

from pathlib import Path


class DirectoryArchiveWrapper:
    """A minimal directory-backed wrapper exposing the same interface subset as ArchiveWrapper.

    Only implements what's needed by LeakProcessor: `filename`, `namelist()`, and `read_file()`.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        if not self.root_dir.exists() or not self.root_dir.is_dir():
            raise ValueError(f"Not a directory: {root_dir}")
        self._filename = str(self.root_dir)

    @property
    def filename(self) -> str:
        return self._filename

    def namelist(self) -> list[str]:
        entries: list[str] = []
        for p in self.root_dir.rglob("*"):
            rel = p.relative_to(self.root_dir).as_posix()
            if p.is_dir():
                entries.append(rel + "/")
            else:
                entries.append(rel)
        return entries

    def read_file(self, filename: str) -> str:
        path = (self.root_dir / filename).resolve()
        if not path.is_file():
            raise KeyError("Not found.")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        return text.replace("\x00", "\\00")

    def close(self) -> None:
        return None
