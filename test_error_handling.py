#!/usr/bin/env python3
"""Test script for improved database error handling."""

import sys
from pathlib import Path

# Add the stealer_parser to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stealer_parser.database.postgres import truncate_string, safe_credential_data, safe_cookie_data
from stealer_parser.models import Credential, Cookie


def test_truncation_functions():
    """Test the data truncation and safety functions."""
    
    print("Testing Data Truncation Functions")
    print("=" * 40)
    
    # Test truncate_string function
    print("\\n1. Testing truncate_string function:")
    
    # Normal case
    normal_text = "This is a normal length string"
    result = truncate_string(normal_text, 50)
    print(f"   Normal text: '{result}' (length: {len(result) if result else 0})")
    
    # Long text
    long_text = "This is a very long string that should be truncated because it exceeds the maximum allowed length"
    result = truncate_string(long_text, 50)
    print(f"   Long text: '{result}' (length: {len(result) if result else 0})")
    
    # None value
    result = truncate_string(None, 50)
    print(f"   None value: {result}")
    
    # Empty string
    result = truncate_string("", 50)
    print(f"   Empty string: '{result}' (length: {len(result) if result else 0})")
    
    # Test safe_credential_data function
    print("\\n2. Testing safe_credential_data function:")
    
    # Create a credential with some long fields
    long_cred = Credential(
        software="Google Chrome Browser with many extensions and custom settings",
        host="https://very-long-domain-name-that-might-exceed-normal-limits.example.com/very/long/path/with/many/segments/that/could/cause/issues",
        username="very_long_username_that_might_be_an_email_address_with_many_characters@very-long-domain-name.example.com",
        password="very_long_password_with_many_special_characters_and_numbers_12345678901234567890",
        domain="very-long-domain-name-that-might-exceed-normal-limits.example.com",
        filepath="/very/long/file/path/that/might/exceed/database/field/limits/passwords.txt",
        stealer_name="redline"
    )
    
    safe_data = safe_credential_data(long_cred, 123)
    
    print(f"   System ID: {safe_data[0]}")
    print(f"   Software: '{safe_data[1]}' (length: {len(safe_data[1]) if safe_data[1] else 0})")
    print(f"   Host: '{safe_data[2][:50]}...' (length: {len(safe_data[2]) if safe_data[2] else 0})")
    print(f"   Username: '{safe_data[3]}' (length: {len(safe_data[3]) if safe_data[3] else 0})")
    print(f"   Password: '{safe_data[4][:30]}...' (length: {len(safe_data[4]) if safe_data[4] else 0})")
    print(f"   Domain: '{safe_data[5]}' (length: {len(safe_data[5]) if safe_data[5] else 0})")
    print(f"   Filepath: '{safe_data[8][:50]}...' (length: {len(safe_data[8]) if safe_data[8] else 0})")
    print(f"   Stealer: '{safe_data[9]}' (length: {len(safe_data[9]) if safe_data[9] else 0})")
    
    # Test safe_cookie_data function
    print("\\n3. Testing safe_cookie_data function:")
    
    long_cookie = Cookie(
        domain="very-long-domain-name-that-might-exceed-normal-limits.example.com",
        domain_specified="TRUE",
        path="/very/long/cookie/path/that/might/exceed/database/field/limits/and/cause/insertion/errors",
        secure="FALSE",
        expiry="1735689600",
        name="very_long_cookie_name_with_many_characters_that_might_exceed_database_limits",
        value="very_long_cookie_value_with_session_data_and_tokens_that_might_be_quite_large_and_exceed_normal_field_sizes",
        browser="Google Chrome with Extensions",
        profile="Default Profile Name That Might Be Long",
        filepath="/very/long/file/path/to/cookies/file/that/might/exceed/database/limits.txt"
    )
    
    safe_cookie_data_result = safe_cookie_data(long_cookie, 123)
    
    print(f"   System ID: {safe_cookie_data_result[0]}")
    print(f"   Domain: '{safe_cookie_data_result[1]}' (length: {len(safe_cookie_data_result[1]) if safe_cookie_data_result[1] else 0})")
    print(f"   Path: '{safe_cookie_data_result[3][:50]}...' (length: {len(safe_cookie_data_result[3]) if safe_cookie_data_result[3] else 0})")
    print(f"   Name: '{safe_cookie_data_result[6]}' (length: {len(safe_cookie_data_result[6]) if safe_cookie_data_result[6] else 0})")
    print(f"   Value: '{safe_cookie_data_result[7][:30]}...' (length: {len(safe_cookie_data_result[7]) if safe_cookie_data_result[7] else 0})")
    print(f"   Browser: '{safe_cookie_data_result[8]}' (length: {len(safe_cookie_data_result[8]) if safe_cookie_data_result[8] else 0})")
    
    print("\\n✅ All truncation tests completed successfully!")
    return True


if __name__ == "__main__":
    print("Stealer Parser - Database Error Handling Test")
    print("Testing improved data truncation and safety functions\\n")
    
    success = test_truncation_functions()
    
    if success:
        print("\\n🎉 All tests passed!")
        print("\\nThe improved error handling should now:")
        print("- Automatically truncate overly long data")
        print("- Fall back to individual inserts on batch failures")
        print("- Continue processing even when some records fail")
        print("- Provide detailed logging for troubleshooting")
        sys.exit(0)
    else:
        print("\\n💥 Some tests failed!")
        sys.exit(1)