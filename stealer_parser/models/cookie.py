"""Data model to define browser cookies found in leaks."""
from dataclasses import dataclass
from datetime import datetime

from .types import StealerNameType


@dataclass
class Cookie:
    """Class defining a browser cookie.
    
    Follows the Netscape cookie jar format with 7 tab-delimited fields:
    domain, domain_specified, path, secure, expiry, name, value
    
    Attributes
    ----------
    domain : str
        The domain that created and can access the cookie
    domain_specified : bool
        Whether the domain was explicitly specified
    path : str
        The path within the domain where cookie is valid
    secure : bool
        Whether cookie should only be transmitted over secure HTTPS
    expiry : datetime
        When the cookie expires
    name : str
        The name of the cookie
    value : str
        The cookie's value
    browser : str, optional
        The browser the cookie was extracted from
    profile : str, optional
        The browser profile the cookie was extracted from
    filepath : str, optional
        The cookie file path
    stealer_name : stealer_parser.models.types.StealerType, optional
        If applicable, the stealer that harvested the data
    """

    domain: str
    domain_specified: str
    path: str
    secure: str 
    expiry: str
    name: str
    value: str
    browser: str | None = None
    profile: str = "unknown"
    filepath: str | None = None
    stealer_name: StealerNameType | None = None
