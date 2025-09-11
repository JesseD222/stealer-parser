"""Parser for Netscape cookie jar format files."""
import logging
from datetime import datetime
from pathlib import Path

from ..models.cookie import Cookie

logger = logging.getLogger(__name__)

def parse_cookie_file(filepath: str | Path, browser: str | None = None) -> list[Cookie]:
    """Parse a Netscape cookie jar format file.
    
    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the cookie file
    browser : str, optional
        Name of the browser the cookies are from
        
    Returns
    -------
    list of stealer_parser.models.cookie.Cookie
        The parsed cookies
        
    """
    cookies = []
    
    # Convert string path to Path object if needed
    if isinstance(filepath, str):
        filepath = Path(filepath)
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                try:
                    # Split on tabs - Netscape format has 7 tab-delimited fields
                    fields = line.split('\t')
                    if len(fields) != 7:
                        logger.warning(f"Invalid cookie line in {filepath}: {line}")
                        continue
                        
                    domain, domain_specified, path, secure, expiry, name, value = fields
                    
                    # Convert fields to appropriate types
                    domain_specified = domain_specified.lower() == 'true'
                    secure = secure.lower() == 'true'
                    try:
                        expiry = datetime.fromtimestamp(int(expiry))
                    except ValueError:
                        logger.warning(f"Invalid expiry timestamp in {filepath}: {expiry}")
                        expiry = datetime.max
                        
                    cookie = Cookie(
                        domain=domain,
                        domain_specified=domain_specified,
                        path=path,
                        secure=secure,
                        expiry=expiry,
                        name=name,
                        value=value,
                        browser=browser,
                        filepath=str(filepath)
                    )
                    cookies.append(cookie)
                    
                except Exception as e:
                    logger.warning(f"Error parsing cookie line in {filepath}: {line}")
                    logger.warning(f"Error details: {str(e)}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error reading cookie file {filepath}")
        logger.error(f"Error details: {str(e)}")
        
    return cookies
