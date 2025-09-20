from __future__ import annotations

from pathlib import Path
from typing import List
from pydantic import BaseModel
import json
import yaml

from .definitions import RecordDefinition


class DefinitionStore(BaseModel):
    base_dirs: List[Path]

    class Config:
        arbitrary_types_allowed = True

    def load_all(self) -> List[RecordDefinition]:
        defs: List[RecordDefinition] = []
        for base in self.base_dirs:
            if not base.exists():
                continue
            for p in base.rglob("*.yml"):
                defs.append(RecordDefinition.model_validate(yaml.safe_load(p.read_text())))
            for p in base.rglob("*.yaml"):
                defs.append(RecordDefinition.model_validate(yaml.safe_load(p.read_text())))
            for p in base.rglob("*.json"):
                defs.append(RecordDefinition.model_validate(json.loads(p.read_text())))
        return defs
