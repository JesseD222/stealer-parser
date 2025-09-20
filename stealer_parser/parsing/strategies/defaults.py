from __future__ import annotations

from typing import Iterable, Set
import re

from ..definitions import RecordDefinition
from ..factory import Chunker, Extractor, Transformer


class RegexSeparatorChunker(Chunker):
    def capabilities(self) -> Set[str]:
        return {"regex-boundary", "multiline"}

    def chunk(self, text: Iterable[str], definition: RecordDefinition) -> Iterable[list[str]]:
        seps = definition.compiled["separators"]
        buf: list[str] = []
        for ln in text:
            if seps and any(sep.search(ln) for sep in seps):
                if buf:
                    yield buf
                    buf = []
                continue
            buf.append(ln)
        if buf:
            yield buf


class KVHeaderExtractor(Extractor):
    def capabilities(self) -> Set[str]:
        return {"kv-headers"}

    def extract(self, lines: list[str], definition: RecordDefinition) -> dict:
        delims = definition.compiled["delims"]
        headers = definition.compiled["headers"]
        data: dict = {}
        for ln in lines:
            if any(h.search(ln) for h in headers):
                key = None
                val = None
                for d in delims:
                    m = d.search(ln)
                    if m:
                        key = ln[: m.start()].strip()
                        val = ln[m.end() :].strip()
                        break
                if key is not None:
                    data.setdefault("_order", []).append(key)
                    data[key] = val
        return data


class AliasGroupingTransformer(Transformer):
    def capabilities(self) -> Set[str]:
        return {"grouping", "kv-headers"}

    def transform(self, raw: dict, definition: RecordDefinition) -> dict:
        if not raw:
            return {}
        result: dict = {"type": definition.key, "fields": {}, "groups": {}}
        field_map = {f.name: f for f in definition.fields}
        for fname, fdef in field_map.items():
            candidates = [a.lower() for a in ([fname] + fdef.aliases)]
            match = next(
                (k for k in raw.keys() if isinstance(k, str) and k.lower() in candidates),
                None,
            )
            if match:
                result["fields"][fname] = raw.get(match)
                if fdef.group:
                    result["groups"].setdefault(fdef.group, {})[fname] = raw.get(match)
        return result


class LineChunker(Chunker):
    def capabilities(self) -> Set[str]:
        return {"line-based"}

    def chunk(self, text: Iterable[str], definition: RecordDefinition) -> Iterable[list[str]]:
        for ln in text:
            if not ln or ln.startswith("#"):
                continue
            yield [ln]


class DelimitedLineExtractor(Extractor):
    def capabilities(self) -> Set[str]:
        return {"line-based"}

    def extract(self, lines: list[str], definition: RecordDefinition) -> dict:
        # Expect a single line per chunk
        if not lines:
            return {}
        line = lines[0]
        # Try tabs first, then whitespace
        parts = line.split("\t")
        if len(parts) != 7:
            import re as _re
            parts = _re.split(r"\s+", line, maxsplit=6)
            if len(parts) != 7:
                return {}
        # Map to canonical names commonly used in cookies
        keys = [
            "domain",
            "domain_specified",
            "path",
            "secure",
            "expiry",
            "name",
            "value",
        ]
        return {k: v for k, v in zip(keys, parts)}


class FullFileChunker(Chunker):
    def capabilities(self) -> Set[str]:
        return {"full-file", "vault", "regex-boundary", "multiline"}

    def chunk(self, text: Iterable[str], definition: RecordDefinition) -> Iterable[list[str]]:
        all_lines = list(text)
        if all_lines:
            yield all_lines


class VaultExtractor(Extractor):
    def capabilities(self) -> Set[str]:
        return {"vault", "full-file"}

    def extract(self, lines: list[str], definition: RecordDefinition) -> dict:
        import json
        import re as _re

        content = "\n".join(lines).strip()
        lowered = content.lower()
        # Only emit a record when we have strong evidence of a vault/keystore

        # JSON keystore (MetaMask and similar) detection
        parsed: dict | None = None
        if content.lstrip().startswith("{"):
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = None

        # Electrum-like JSON
        if parsed and isinstance(parsed, dict) and ("seed_version" in parsed or "wallet_type" in parsed):
            return {"vault_type": "electrum", "vault_data": content[:4000], "seed_words": "", "key_phrase": ""}

        # Ethereum/keystore JSON
        if parsed and isinstance(parsed, dict) and (
            "crypto" in parsed or "Crypto" in parsed or "version" in parsed
        ):
            vault_type = "metamask" if "metamask" in lowered else "generic"

            crypto = parsed.get("crypto") or parsed.get("Crypto") or {}
            result = {
                "vault_type": vault_type,
                "vault_data": content[:4000],
                "keystore_address": parsed.get("address"),
                "keystore_kdf": (crypto.get("kdf") if isinstance(crypto, dict) else None),
                "keystore_cipher": (crypto.get("cipher") if isinstance(crypto, dict) else None),
                "key_phrase": "",
                "seed_words": "",
            }
            return result

        # Non-JSON hints: Bitcoin wallet.dat (SQLite detectable via decoded header)
        if "sqlite format 3" in lowered or "wallet.dat" in lowered:
            return {"vault_type": "bitcoin", "vault_data": content[:4000], "key_phrase": "", "seed_words": ""}

        # Heuristic extraction for LevelDB/log MetaMask-like JSON fragments
        # Remove backslashes to recover JSON-like structures
        de_escaped = content.replace("\\", "")
        # Patterns matching common keystore fragments in logs/ldb
        patterns = [
            r"\{[^{}]*\"data\"\s*:\s*\".+?\"[^{}]*\"iv\"\s*:\s*\".+?\"[^{}]*\"salt\"\s*:\s*\".+?\"[^{}]*\}",
            r"\{[^{}]*\"encrypted\"\s*:\s*\".+?\"[^{}]*\"nonce\"\s*:\s*\".+?\"[^{}]*\"kdf\"\s*:\s*\"(?:pbkdf2|scrypt)\"[^{}]*\"salt\"\s*:\s*\".+?\"[^{}]*\}",
            r"\{[^{}]*\"ct\"\s*:\s*\".+?\"[^{}]*\"iv\"\s*:\s*\".+?\"[^{}]*\"s\"\s*:\s*\".+?\"[^{}]*\}",
        ]
        found = None
        for pat in patterns:
            m_iter = list(_re.finditer(pat, de_escaped, flags=_re.S))
            if m_iter:
                found = m_iter[-1].group(0)
                break

        if found:
            try:
                data_obj = json.loads(found)
            except Exception:
                data_obj = None
            return {
                "vault_type": "metamask",
                "vault_data": (found[:4000] if isinstance(found, str) else content[:4000]),
                "keystore_kdf": (data_obj.get("kdf") if isinstance(data_obj, dict) else None),
                "keystore_cipher": (data_obj.get("cipher") if isinstance(data_obj, dict) else None),
                "key_phrase": "",
                "seed_words": "",
            }

        # No strong evidence; don't emit a vault record to avoid false positives
        return {}


class VaultTransformer(Transformer):
    def capabilities(self) -> Set[str]:
        return {"vault", "full-file"}

    def transform(self, raw: dict, definition: RecordDefinition) -> dict:
        if not raw:
            return {}
        out = {"type": definition.key}
        out.update(raw)
        return out
