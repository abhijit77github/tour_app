"""Email sending utilities for OTP and notifications"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


def send_otp_email(
    recipient_email: str,
    otp: str,
    full_name: Optional[str] = None
) -> bool:
    """
    Send OTP email for password reset
    
    Args:
        recipient_email: Email address of the recipient
        otp: One-time password
        full_name: Optional full name of the user
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Email configuration
        sender_email = settings.smtp_email or "noreply@tourapp.com"
        sender_password = settings.smtp_password or ""
        smtp_server = settings.smtp_server or "smtp.gmail.com"
        smtp_port = settings.smtp_port or 587
        
        # Skip actual sending if credentials not configured (for development)
        if not settings.smtp_password:
            logger.warning(f"SMTP not configured. OTP for {recipient_email}: {otp}")
            return True
        
        # Create message
        subject = "Password Reset OTP - Tour App"
        
        # HTML email template
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Password Reset Request</h2>
                    
                    {"<p style='color: #666;'>Hi " + full_name + ",</p>" if full_name else "<p style='color: #666;'>Hi there,</p>"}
                    
                    <p style="color: #666; line-height: 1.6;">
                        We received a request to reset your password. Use the OTP below to proceed with the password reset:
                    </p>
                    
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 4px; margin: 20px 0; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; margin: 0;">
                            {otp}
                        </p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        <strong>This OTP will expire in 10 minutes.</strong>
                    </p>
                    
                    <p style="color: #666; line-height: 1.6;">
                        If you didn't request a password reset, please ignore this email or contact our support team immediately.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        Tour App Security Team<br>
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
Password Reset OTP - Tour App

{"Hi " + full_name + "," if full_name else "Hi there,"}

We received a request to reset your password. Use the OTP below to proceed:

{otp}

This OTP will expire in 10 minutes.

If you didn't request this, please ignore this email.

Tour App Security Team
        """
        
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"OTP email sent successfully to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check email credentials.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending OTP email: {str(e)}")
        return False


def send_password_reset_confirmation_email(
    recipient_email: str,
    full_name: Optional[str] = None
) -> bool:
    """
    Send confirmation email after successful password reset
    
    Args:
        recipient_email: Email address of the recipient
        full_name: Optional full name of the user
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        sender_email = settings.smtp_email or "noreply@tourapp.com"
        sender_password = settings.smtp_password or ""
        smtp_server = settings.smtp_server or "smtp.gmail.com"
        smtp_port = settings.smtp_port or 587
        
        if not settings.smtp_password:
            logger.warning(f"SMTP not configured. Password reset confirmation for {recipient_email}")
            return True
        
        subject = "Password Reset Successful - Tour App"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #27ae60; margin-bottom: 20px;">✓ Password Reset Successful</h2>
                    
                    {"<p style='color: #666;'>Hi " + full_name + ",</p>" if full_name else "<p style='color: #666;'>Hi there,</p>"}
                    
                    <p style="color: #666; line-height: 1.6;">
                        Your password has been successfully reset. You can now log in with your new password.
                    </p>
                    
                    <p style="color: #666; line-height: 1.6;">
                        If you didn't make this change, please contact our support team immediately.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        Tour App Security Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
Password Reset Successful - Tour App

{"Hi " + full_name + "," if full_name else "Hi there,"}

Your password has been successfully reset. You can now log in with your new password.

If you didn't make this change, please contact support immediately.

Tour App Security Team
        """
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"Password reset confirmation email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}")
        return False

