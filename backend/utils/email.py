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
    full_name: Optional[str] = None,
    purpose: str = "password_reset",
    validity_minutes: int = 10,
) -> bool:
    """
    Send OTP email for account activation or password reset
    
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
        
        if purpose == "account_activation":
            subject = "Verify your email - Tour Local"
            heading = "Activate Your Account"
            intro = "Use the OTP below to verify your email address and activate your account:"
            closing = "If you did not create this account, you can safely ignore this email."
            team_name = "Tour Local Team"
        else:
            subject = "Password Reset OTP - Tour Local"
            heading = "Password Reset Request"
            intro = "We received a request to reset your password. Use the OTP below to proceed with the password reset:"
            closing = "If you didn't request a password reset, please ignore this email or contact our support team immediately."
            team_name = "Tour Local Security Team"
        
        # HTML email template
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">{heading}</h2>
                    
                    {"<p style='color: #666;'>Hi " + full_name + ",</p>" if full_name else "<p style='color: #666;'>Hi there,</p>"}
                    
                    <p style="color: #666; line-height: 1.6;">{intro}</p>
                    
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 4px; margin: 20px 0; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; margin: 0;">
                            {otp}
                        </p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        <strong>This OTP will expire in {validity_minutes} minutes.</strong>
                    </p>
                    
                    <p style="color: #666; line-height: 1.6;">{closing}</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        {team_name}<br>
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
{heading} - Tour Local

{"Hi " + full_name + "," if full_name else "Hi there,"}

{intro}

{otp}

This OTP will expire in {validity_minutes} minutes.

{closing}

{team_name}
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
        
        subject = "Password Reset Successful - Tour Local"
        
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
                        Tour Local Security Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
Password Reset Successful - Tour Local

{"Hi " + full_name + "," if full_name else "Hi there,"}

Your password has been successfully reset. You can now log in with your new password.

If you didn't make this change, please contact support immediately.

Tour Local Security Team
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


def send_support_ticket_status_email(
    recipient_email: str,
    *,
    ticket_id: str,
    ticket_title: str,
    status_value: str,
    full_name: Optional[str] = None,
    public_reply: Optional[str] = None,
) -> bool:
    """Send an automated support ticket status update email."""
    try:
        sender_email = settings.smtp_email or "noreply@tourapp.com"
        sender_password = settings.smtp_password or ""
        smtp_server = settings.smtp_server or "smtp.gmail.com"
        smtp_port = settings.smtp_port or 587

        subject = f"Support Ticket {status_value.replace('_', ' ').title()} - Tour Local"
        greeting = f"Hi {full_name}," if full_name else "Hi there,"
        status_copy = {
            "acknowledged": "Your support ticket has been acknowledged by our admin team.",
            "in_progress": "Your support ticket is currently being worked on.",
            "completed": "Your support ticket has been marked as completed.",
        }.get(status_value, "Your support ticket has been updated.")

        reply_block_html = ""
        reply_block_text = ""
        if public_reply:
            reply_block_html = f"""
                <div style=\"background:#f8fafc;padding:16px;border-radius:8px;margin:18px 0;\">
                    <p style=\"margin:0 0 6px;color:#334155;font-weight:600;\">Admin reply</p>
                    <p style=\"margin:0;color:#475569;line-height:1.6;\">{public_reply}</p>
                </div>
            """
            reply_block_text = f"\nAdmin reply:\n{public_reply}\n"

        if not settings.smtp_password:
            logger.warning(
                "SMTP not configured. Support ticket status email for %s: ticket=%s status=%s",
                recipient_email,
                ticket_id,
                status_value,
            )
            return True

        html_content = f"""
        <html>
          <body style=\"font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;\">
            <div style=\"background:white;max-width:600px;margin:0 auto;padding:30px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);\">
              <h2 style=\"color:#0f172a;margin-bottom:18px;\">Support ticket update</h2>
              <p style=\"color:#475569;\">{greeting}</p>
              <p style=\"color:#475569;line-height:1.6;\">{status_copy}</p>
              <div style=\"background:#eef6ff;padding:16px;border-radius:8px;margin:18px 0;\">
                <p style=\"margin:0 0 6px;color:#334155;font-weight:600;\">Ticket ID</p>
                <p style=\"margin:0 0 10px;color:#0f172a;\">{ticket_id}</p>
                <p style=\"margin:0 0 6px;color:#334155;font-weight:600;\">Subject</p>
                <p style=\"margin:0;color:#0f172a;\">{ticket_title}</p>
              </div>
              {reply_block_html}
              <p style=\"color:#64748b;line-height:1.6;\">You can log in to your operator workspace to review the latest ticket status at any time.</p>
              <p style=\"color:#94a3b8;font-size:12px;margin-top:24px;\">Tour Local Support</p>
            </div>
          </body>
        </html>
        """

        text_content = f"""
Support ticket update - Tour Local

{greeting}

{status_copy}

Ticket ID: {ticket_id}
Subject: {ticket_title}
{reply_block_text}
You can log in to your operator workspace to review the latest ticket status at any time.

Tour Local Support
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
        logger.info("Support ticket status email sent to %s", recipient_email)
        return True
    except Exception as e:
        logger.error(f"Error sending support ticket status email: {str(e)}")
        return False

