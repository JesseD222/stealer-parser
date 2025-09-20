"""Leak processing component."""
from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

from rarfile import BadRarFile
from verboselogs import VerboseLogger

from stealer_parser.models import (
    ArchiveWrapper,
    Credential,
    Leak,
    System,
    SystemData,
    Cookie,
    Vault,
)
from stealer_parser.parsing.parsers.cookie_parser import CookieParser
from stealer_parser.parsing.parsers.password_parser import PasswordParser
from stealer_parser.parsing.parsers.system_parser import SystemParser
from stealer_parser.parsing.registry import ParserRegistry
from stealer_parser.config import Settings


class LeakProcessor:
    """Orchestrates the processing of a leak from an archive."""

    def __init__(self, parser_registry: ParserRegistry, logger: VerboseLogger, settings: Settings | None = None):
        self.parser_registry = parser_registry
        self.logger = logger
        self.settings = settings or Settings()

    def process_leak(self, archive: ArchiveWrapper) -> Leak:
        """
        Process every system directory in an archive.
        """
        self.logger.info(f"Processing: {archive.filename} ...")
        leak = Leak(filename=str(archive.filename))
        systems: dict[str, SystemData] = {}

        try:
            for file_path in archive.namelist():
                if file_path.endswith('/'):
                    continue

                # Prefer definition-backed parser if enabled
                parser = None
                try:
                    if getattr(self.settings, "prefer_definition_parsers", False):
                        sample_full = archive.read_file(file_path)
                        sample_text = sample_full[:12000]
                        parser = self.parser_registry.find_best_for(Path(file_path), sample_text, threshold=self.settings.parser_match_threshold)
                except Exception:
                    parser = None
                if not parser:
                    parser = self.parser_registry.get_parser(file_path)
                if not parser:
                    continue

                system_dir = self._get_system_dir(file_path)

                if system_dir not in systems:
                    systems[system_dir] = SystemData(system=System())

                system_data = systems[system_dir]

                try:
                    text = archive.read_file(file_path)
                    if isinstance(parser, CookieParser):
                        parse_kwargs = {
                            "filename": file_path,
                            "browser": self._infer_browser(file_path),
                            "profile": self._infer_profile(file_path),
                        }
                        cookie_results = parser.parse(text, **parse_kwargs)
                        for cookie in cookie_results:
                            system_data.cookies.append(cookie)
                    elif isinstance(parser, PasswordParser):
                        cred_results = parser.parse(text)
                        for cred in cred_results:
                            system_data.credentials.append(cred)
                    elif isinstance(parser, SystemParser):
                        sys_results = parser.parse(text)
                        for info in sys_results:
                            if isinstance(info, dict):
                                for key, value in info.items():
                                    if hasattr(system_data.system, key):
                                        setattr(system_data.system, key, value)
                    else:
                        # Configurable parser path: map known types
                        _kwargs = {"filename": file_path} if parser.__class__.__name__ == "ConfigurableParser" else {}
                        generic_results = parser.parse(text, **_kwargs)
                        iterable = generic_results if isinstance(generic_results, list) else [generic_results]
                        for rec in iterable:
                            if isinstance(rec, dict) and rec.get("type") == "vault":
                                # Prefer values captured by definition path_extractors; fallback to inference
                                rb = rec.get("browser")
                                rp = rec.get("profile")
                                vb, vp = (rb or None, rp or None)
                                if vb is None or vp is None:
                                    fb, fp = self._infer_vault_browser_profile(file_path)
                                    vb = vb or fb
                                    vp = vp or fp
                                v = Vault(
                                    vault_type=rec.get("vault_type"),
                                    title=rec.get("title"),
                                    url=rec.get("url"),
                                    username=rec.get("username"),
                                    password=rec.get("password"),
                                    notes=rec.get("notes"),
                                    vault_data=rec.get("vault_data"),
                                    key_phrase=rec.get("key_phrase"),
                                    seed_words=rec.get("seed_words"),
                                    filepath=file_path,
                                    browser=vb or "unknown",
                                    profile=vp or "unknown",
                                )
                                system_data.vaults.append(v)
                            elif isinstance(rec, dict) and rec.get("type") == "cookie":
                                f = rec.get("fields") if isinstance(rec.get("fields"), dict) else rec
                                if f:
                                    cb = rec.get("browser") or self._infer_browser(file_path) or "unknown"
                                    cp = rec.get("profile") or self._infer_profile(file_path) or "unknown"
                                    cookie = Cookie(
                                        domain=f.get("domain", ""),
                                        domain_specified=f.get("domain_specified", ""),
                                        path=f.get("path", ""),
                                        secure=f.get("secure", ""),
                                        expiry=f.get("expiry", ""),
                                        name=f.get("name", ""),
                                        value=f.get("value", ""),
                                        browser=cb,
                                        profile=cp,
                                        filepath=file_path,
                                    )
                                    system_data.cookies.append(cookie)

                    self.logger.debug(f"Successfully parsed {file_path} with {parser.__class__.__name__}")
                except (BadRarFile) as e:
                    self.logger.error(f"Failed to read {file_path} from archive: {e}")
                except Exception as e:
                    self.logger.error(f"Unexpected error parsing {file_path} with {parser.__class__.__name__}: {e}")

            for system_data in systems.values():
                leak.systems.append(system_data)

        except BadRarFile as err:
            raise BadRarFile(f"BadRarFile: {err}") from err
        except RuntimeError as err:  # The archive was closed.
            self.logger.error(err)

        self.logger.debug(f"Parsed '{leak.filename}' ({len(leak.systems)} systems).")
        return leak

    def _get_system_dir(self, filepath: str) -> str:
        """Retrieve name of the compromised system directory."""
        parts = filepath.split('/')
        return parts[0] if len(parts) > 1 else ''

    def _infer_browser(self, filepath: str) -> str:
        fp = filepath.lower()
        if "chrome" in fp:
            return "chrome"
        if "brave" in fp:
            return "brave"
        if "edge" in fp:
            return "edge"
        if "firefox" in fp:
            return "firefox"
        return "unknown"

    def _infer_profile(self, filepath: str) -> str:
        parts = filepath.split('/')
        for i, part in enumerate(parts):
            if part.lower() in ("default", "profile 1", "profile1", "profile 2", "profile2"):
                return part
        return "unknown"

    def _infer_vault_browser_profile(self, filepath: str) -> tuple[str, str]:
        # Expected pattern: ROOT/Wallets/BrowserName ProfileName/...
        parts = filepath.split('/')
        try:
            wallet_idx = next(i for i, p in enumerate(parts) if p.lower() == "wallets")
        except StopIteration:
            return (self._infer_browser(filepath), self._infer_profile(filepath))
        # The next segment should be "BrowserName ProfileName"
        if wallet_idx + 1 < len(parts):
            combo = parts[wallet_idx + 1]
            # Try to split last space into browser and profile
            if " " in combo:
                browser = combo.split(" ")[0]
                profile = combo[len(browser) + 1 :]
                return (browser, profile)
            # Fallback: treat whole as browser and infer profile normally
            return (combo, self._infer_profile(filepath))
        return (self._infer_browser(filepath), self._infer_profile(filepath))

