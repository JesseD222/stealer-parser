"""Data model to define password manager vault entries found in leaks."""
from dataclasses import dataclass
from .types import StealerNameType


@dataclass
class Vault:
    """Class defining a vault entry or vault artifact.

    Attributes
    ----------
    vault_type : str, optional
        The vault/wallet type (e.g., metamask, bitcoin, electrum, generic).
    title : str, optional
        Entry title or service label.
    url : str, optional
        Associated site URL.
    username : str, optional
        Login username/email for this entry.
    password : str, optional
        Decrypted password if available.
    notes : str, optional
        Notes or additional metadata.
    vault_data : str, optional
        Raw JSON or excerpted content when applicable.
    key_phrase : str, optional
        Recovery phrase if present.
    seed_words : str, optional
        Seed words when relevant.
    filepath : str, optional
        Source file path in the leak.
    stealer_name : stealer_parser.models.types.StealerType, optional
        If applicable, the stealer that harvested the data.
    browser : str, optional
        The browser the vault artifact was extracted from (e.g., Chrome, Brave).
    profile : str, optional
        The browser profile the vault artifact was extracted from (e.g., Default, Profile 1).
    """

    vault_type: str | None = None
    title: str | None = None
    url: str | None = None
    username: str | None = None
    password: str | None = None
    notes: str | None = None
    vault_data: str | None = None
    key_phrase: str | None = None
    seed_words: str | None = None
    filepath: str | None = None
    stealer_name: StealerNameType | None = None
    browser: str | None = None
    profile: str = "unknown"
