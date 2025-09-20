"""Data model to define a leak's content.

- Metadata: contextual information (origin, date, size, ...)
- Compromised systems found in the leak
- Credentials found in the leak, sorted by system.
"""
from dataclasses import dataclass, field

from .credential import Credential
from .cookie import Cookie
from .system import System
from .types import StealerNameType


@dataclass
class SystemData:
    """Class defining a system's leaked data.

    Attributes
    ----------
    system : leak : stealer_parser.models.system.System, optional
        The compromised system information.
    credentials : list of stealer_parser.models.credential.Credential, optional
        The leaked credentials.
    cookies : list of stealer_parser.models.cookie.Cookie, optional
        The leaked browser cookies.

    Methods
    -------
    add_stealer_name(stealer_name)
        Add stealer name to every credentials and cookies.

    """

    system: System | None = None
    credentials: list[Credential] = field(default_factory=list)
    cookies: list[Cookie] = field(default_factory=list)

    def add_stealer_name(self, stealer_name: StealerNameType) -> None:
        """Add stealer name to every credentials and cookies.

        Intended to be called once the whole system folder has been processed
        since the name can be found after the password file was parsed.

        Parameters
        ----------
        stealer_name : stealer_parser.models.types.StealerType
            The stealer name.

        """
        for credential in self.credentials:
            credential.stealer_name = stealer_name
        for cookie in self.cookies:
            cookie.stealer_name = stealer_name


@dataclass
class Leak:
    """Class defining a leak (metadata and content).

    Attributes
    ----------
    filename : str
        The archive file name.
    systems : list of SystemData
        The list of compromised systems.
    stealer_name : StealerNameType, optional
        The name of the stealer.

    """

    filename: str
    systems: list[SystemData] = field(default_factory=list)
    stealer_name: StealerNameType | None = None
