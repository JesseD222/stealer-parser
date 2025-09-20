from __future__ import annotations

from pathlib import Path
from typing import Iterable
import fnmatch

from .definitions import RecordDefinition


def score_definition(
    path: Path, sample_lines: Iterable[str], definition: RecordDefinition
) -> float:
    lines = list(sample_lines)
    weights = definition.score_weights
    score = 0.0

    # path-based signal
    if any(fnmatch.fnmatch(str(path), pat) for pat in definition.file_globs):
        score += weights.get("path", 1.0)

    # content-based signals
    sep_hits = sum(
        1 for ln in lines for sep in definition.compiled["separators"] if sep.search(ln)
    )
    hdr_hits = sum(
        1 for ln in lines for hdr in definition.compiled["headers"] if hdr.search(ln)
    )
    alias_hits = sum(
        1 for ln in lines for al in definition.compiled["aliases"] if al.search(ln)
    )

    score += sep_hits * weights.get("separator", 1.0)
    score += hdr_hits * weights.get("header", 2.0)
    score += alias_hits * weights.get("alias", 0.5)

    denom = max(10, len(lines))
    return score / denom
