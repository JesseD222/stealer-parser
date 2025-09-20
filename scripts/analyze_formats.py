from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

from stealer_parser.models.archive_wrapper import ArchiveWrapper
from stealer_parser.models.directory_wrapper import DirectoryArchiveWrapper

try:
    from py7zr import SevenZipFile
except Exception:
    SevenZipFile = None  # type: ignore

try:
    from rarfile import RarFile
except Exception:
    RarFile = None  # type: ignore


def open_path_as_archive(path: Path):
    if path.is_dir():
        return DirectoryArchiveWrapper(path)
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return ArchiveWrapper(ZipFile(BytesIO(data)), filename=str(path))
    if suffix == ".7z" and SevenZipFile is not None:
        return ArchiveWrapper(SevenZipFile(BytesIO(data)), filename=str(path))
    if suffix == ".rar" and RarFile is not None:
        return ArchiveWrapper(RarFile(BytesIO(data)), filename=str(path))
    raise ValueError(f"Unsupported path: {path}")


def iter_lines(text: str, limit: int | None = None) -> Iterable[str]:
    cnt = 0
    for ln in text.splitlines():
        yield ln
        cnt += 1
        if limit and cnt >= limit:
            break


def analyze_file(name: str, text: str) -> dict:
    lines = list(iter_lines(text, 1000))
    total = len(lines)

    # delimiter & header analysis
    colon = sum(1 for ln in lines if ":" in ln)
    equals = sum(1 for ln in lines if "=" in ln)
    tabs = sum(1 for ln in lines if "\t" in ln)

    # regex separators
    dashes = sum(1 for ln in lines if re.match(r"^-{2,}\s*$", ln))
    blanks = sum(1 for ln in lines if re.match(r"^\s*$", ln))

    # header-like lines (label: value)
    header_like = [ln for ln in lines if re.match(r"^[A-Za-z][\w \-/]{0,40}\s*[:=]\s*", ln)]
    header_keys = [re.split(r"[:=]", ln, maxsplit=1)[0].strip().lower() for ln in header_like]
    header_top = Counter(header_keys).most_common(12)

    # cookie-like lines (netscape 7-column)
    cookie_like = 0
    cookie_spaces = 0
    cookie_tab = 0
    for ln in lines:
        parts_tab = ln.split("\t")
        if len(parts_tab) == 7:
            cookie_like += 1
            cookie_tab += 1
            continue
        parts_ws = re.split(r"\s+", ln)
        if len(parts_ws) == 7:
            cookie_like += 1
            cookie_spaces += 1

    # line length stats
    lens = [len(ln) for ln in lines if ln]
    lens.sort()
    def pct(p: float) -> int:
        if not lens:
            return 0
        idx = min(len(lens) - 1, max(0, int(p * (len(lens) - 1))))
        return lens[idx]

    # guess type
    low = name.lower()
    guess = []
    if "cookies/" in low or name.lower().endswith("cookies.txt"):
        guess.append("cookies")
    if "system" in low:
        guess.append("system")
    if "password" in low or "all passwords" in low or "brute" in low:
        guess.append("credential")

    return {
        "file": name,
        "total_lines": total,
        "delims": {":": colon, "=": equals, "\t": tabs},
        "separators": {"dashes": dashes, "blanks": blanks},
        "header_top": header_top,
        "cookie_like": {"any": cookie_like, "tabs": cookie_tab, "spaces": cookie_spaces},
        "line_len": {"p50": pct(0.5), "p90": pct(0.9), "max": max(lens) if lens else 0},
        "guess": guess,
    }


def main():
    ap = argparse.ArgumentParser(description="Analyze stealer log formats")
    ap.add_argument("path", help="Path to data directory or archive (zip/rar/7z)")
    ap.add_argument("--limit", type=int, default=200, help="Max files to analyze")
    args = ap.parse_args()

    path = Path(args.path)
    arc = open_path_as_archive(path)

    results = []
    cookies = defaultdict(int)
    headers = Counter()
    seps = Counter()

    count = 0
    for name in arc.namelist():
        if name.endswith("/"):
            continue
        try:
            text = arc.read_file(name)
        except Exception:
            continue
        info = analyze_file(name, text)
        results.append(info)
        # accumulators
        if info["cookie_like"]["any"]:
            cookies["files_with_cookies_like"] += 1
            cookies["tabs"] += info["cookie_like"]["tabs"]
            cookies["spaces"] += info["cookie_like"]["spaces"]
        for k, v in info["separators"].items():
            seps[k] += v
        for hk, cnt in info["header_top"]:
            headers[hk] += cnt

        count += 1
        if args.limit and count >= args.limit:
            break

    summary = {
        "files_analyzed": count,
        "cookies": cookies,
        "top_headers": headers.most_common(20),
        "separators": dict(seps),
        "samples": results[:10],
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
