"""Parser for Netscape cookie jar format files."""
import logging
from datetime import datetime
from pathlib import Path
from verboselogs import VerboseLogger

from ..models.cookie import Cookie

logger = logging.getLogger(__name__)

def parse_cookie(logger: VerboseLogger, 
                 cookiedata: str, 
                 browser: str | None, 
                 profile: str | None, 
                 filename: str
                 ) -> Cookie | None:
    
    """Parse a single cookie line in Netscape cookie jar format.
    
    Parameters
    ----------
    cookiedata : str
        The raw cookie data as a string.
        
    Returns
    -------
    stealer_parser.models.cookie.Cookie
        The parsed cookie
        
    """
    cookie: Cookie | None = None
    try:
        # Split on tabs - Netscape format has 7 tab-delimited fields
        fields = cookiedata.split('\t')
        if len(fields) != 7:
            logger.warning(f"Invalid cookie data: {cookiedata}")
            return None
            
        domain, domain_specified, path, secure, expiry, name, value = fields
            
        if not browser:
            browser = "unknown"
        if not profile:
            profile = "unknown"

        cookie = Cookie(
            domain=domain,
            domain_specified=domain_specified,
            path=path,
            secure=secure,
            expiry=expiry,
            name=name,
            value=value,
            browser=browser,
            profile=profile,
            filepath=str(filename)
        )
        
    except Exception as e:
        logger.warning(f"Error parsing cookie line: {cookiedata}")
        logger.warning(f"Error details: {str(e)}")
        return None
        
    return cookie

def parse_cookie_file(
    logger: VerboseLogger, filename: str, 
    browser: str | None, 
    profile: str | None,
    text: str
) -> list[Cookie]:

    """Parse a cookies file in Netscape cookie jar format.

    Parameters
    ----------
    logger : verboselogs.VerboseLogger
        The program's logger.
    filename : str
        The file to parse.
    text : str
        The file text content.

    Returns
    -------
    list of stealer_parser.models.cookie.Cookie
        The parsed cookies.

    """
    cookies: list[Cookie] = []

    for line in text.splitlines():
        # Skip empty lines and comments (lines starting with #)
        if not line or line.startswith('#'):
            continue
            
        cookie = parse_cookie(logger, line, browser, profile, filename)
        if cookie:
            cookies.append(cookie)

    return cookies