"""OTP generation and validation utilities"""
import secrets
import string
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# OTP settings
OTP_LENGTH = 6
OTP_VALIDITY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3


def generate_otp() -> str:
    """
    Generate a 6-digit OTP
    
    Returns:
        6-digit OTP as string
    """
    digits = string.digits
    otp = ''.join(secrets.choice(digits) for _ in range(OTP_LENGTH))
    return otp


def is_otp_expired(created_at: datetime) -> bool:
    """
    Check if OTP has expired
    
    Args:
        created_at: When the OTP was created
    
    Returns:
        True if expired, False otherwise
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    expiry_time = created_at + timedelta(minutes=OTP_VALIDITY_MINUTES)
    
    return now > expiry_time


def validate_otp(stored_otp: str, provided_otp: str, created_at: datetime) -> tuple[bool, str]:
    """
    Validate provided OTP against stored OTP
    
    Args:
        stored_otp: OTP stored in database
        provided_otp: OTP provided by user
        created_at: When the OTP was created
    
    Returns:
        Tuple of (is_valid, message)
    """
    if is_otp_expired(created_at):
        return False, "OTP has expired. Please request a new one."
    
    if stored_otp != provided_otp:
        return False, "Invalid OTP. Please check and try again."
    
    return True, "OTP verified successfully"

