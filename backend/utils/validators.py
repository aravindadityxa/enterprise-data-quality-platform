"""
Custom validators for data validation.

Includes validators for emails, phone numbers, dates, and quantities.
"""

import re
from datetime import datetime
from typing import Optional
import phonenumbers
import email_validator


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        email_validator.validate_email(email)
        return True
    except email_validator.EmailNotValidError:
        return False


def validate_phone(phone: str, region: str = "US") -> bool:
    """
    Validate phone number.

    Args:
        phone: Phone number string
        region: Region code (default: US)

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        parsed = phonenumbers.parse(phone, region)
        return phonenumbers.is_valid_number(parsed)
    except phonenumbers.NumberParseException:
        return False


def validate_date(date_str: str, date_formats: Optional[list[str]] = None) -> bool:
    """
    Validate date string.

    Args:
        date_str: Date string to validate
        date_formats: List of date formats to try

    Returns:
        bool: True if valid, False otherwise
    """
    if date_formats is None:
        date_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
        ]

    for fmt in date_formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue

    return False


def validate_negative_quantity(value: float) -> bool:
    """
    Check if quantity is negative.

    Args:
        value: Numeric value

    Returns:
        bool: True if non-negative, False if negative
    """
    try:
        return float(value) >= 0
    except (ValueError, TypeError):
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return url_pattern.match(url) is not None


def normalize_email(email: str) -> str:
    """Normalize email to lowercase."""
    return email.lower().strip()


def normalize_phone(phone: str, region: str = "US") -> Optional[str]:
    """
    Normalize phone number to E.164 format.

    Args:
        phone: Phone number string
        region: Region code

    Returns:
        Optional[str]: Normalized phone number or None if invalid
    """
    try:
        parsed = phonenumbers.parse(phone, region)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None
