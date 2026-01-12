"""Email service using Resend"""
import resend
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def init_resend():
    """Initialize Resend with API key"""
    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY
        return True
    return False


def send_password_reset_email(to_email: str, reset_token: str, user_name: Optional[str] = None) -> bool:
    """
    Send password reset email
    
    Args:
        to_email: Recipient email address
        reset_token: Password reset token
        user_name: Optional user name for personalization
    
    Returns:
        True if email sent successfully, False otherwise
    """
    logger.info(f"[EMAIL] Attempting to send password reset email to {to_email}")
    
    if not settings.RESEND_API_KEY:
        logger.warning(f"[EMAIL] Resend API key not configured!")
        logger.info(f"[EMAIL] Reset link: {settings.FRONTEND_URL}/reset-password?token={reset_token}")
        return False
    
    init_resend()
    
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    greeting = f"Hi {user_name}," if user_name else "Hi,"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f7fa;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 40px 0;">
                    <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 40px 20px; text-align: center; border-bottom: 1px solid #e5e7eb;">
                                <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); border-radius: 12px; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
                                    <span style="font-size: 28px;">📦</span>
                                </div>
                                <h1 style="margin: 0; color: #1f2937; font-size: 24px; font-weight: 600;">{settings.APP_NAME}</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <p style="margin: 0 0 20px; color: #374151; font-size: 16px; line-height: 1.6;">
                                    {greeting}
                                </p>
                                <p style="margin: 0 0 20px; color: #374151; font-size: 16px; line-height: 1.6;">
                                    We received a request to reset your password. Click the button below to create a new password:
                                </p>
                                
                                <!-- Button -->
                                <table role="presentation" style="width: 100%; margin: 30px 0;">
                                    <tr>
                                        <td style="text-align: center;">
                                            <a href="{reset_link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; border-radius: 8px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);">
                                                Reset Password
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 0 0 20px; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                    This link will expire in <strong>24 hours</strong>. If you didn't request this password reset, you can safely ignore this email.
                                </p>
                                
                                <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                    If the button doesn't work, copy and paste this link into your browser:
                                </p>
                                <p style="margin: 10px 0 0; word-break: break-all;">
                                    <a href="{reset_link}" style="color: #2563eb; font-size: 13px;">{reset_link}</a>
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; background-color: #f9fafb; border-top: 1px solid #e5e7eb; border-radius: 0 0 12px 12px;">
                                <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center; line-height: 1.6;">
                                    This is an automated message from {settings.APP_NAME}.<br>
                                    Please do not reply to this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    text_content = f"""
{greeting}

We received a request to reset your password for your {settings.APP_NAME} account.

Click here to reset your password:
{reset_link}

This link will expire in 24 hours.

If you didn't request this password reset, you can safely ignore this email.

---
This is an automated message from {settings.APP_NAME}.
Please do not reply to this email.
    """
    
    try:
        params = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"Reset Your Password - {settings.APP_NAME}",
            "html": html_content,
            "text": text_content,
        }
        
        logger.info(f"[EMAIL] Sending email via Resend to {to_email}...")
        response = resend.Emails.send(params)
        logger.info(f"[EMAIL] Password reset email sent to {to_email}. Response: {response}")
        return True
        
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email to {to_email}: {str(e)}")
        logger.info(f"[EMAIL] Fallback reset link: {settings.FRONTEND_URL}/reset-password?token={reset_token}")
        return False


def send_welcome_email(to_email: str, user_name: str, temp_password: Optional[str] = None) -> bool:
    """
    Send welcome email to new user
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        temp_password: Optional temporary password
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not settings.RESEND_API_KEY:
        print(f"[EMAIL] Resend API key not configured. Welcome email for {to_email}")
        return False
    
    init_resend()
    
    login_link = f"{settings.FRONTEND_URL}/login"
    
    password_section = ""
    if temp_password:
        password_section = f"""
        <p style="margin: 0 0 20px; color: #374151; font-size: 16px; line-height: 1.6;">
            Your temporary password is: <code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{temp_password}</code>
        </p>
        <p style="margin: 0 0 20px; color: #dc2626; font-size: 14px; line-height: 1.6;">
            Please change your password after your first login.
        </p>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to {settings.APP_NAME}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f7fa;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 40px 0;">
                    <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 40px 20px; text-align: center; border-bottom: 1px solid #e5e7eb;">
                                <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); border-radius: 12px; margin: 0 auto 20px;">
                                    <span style="font-size: 28px; line-height: 60px;">📦</span>
                                </div>
                                <h1 style="margin: 0; color: #1f2937; font-size: 24px; font-weight: 600;">Welcome to {settings.APP_NAME}!</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <p style="margin: 0 0 20px; color: #374151; font-size: 16px; line-height: 1.6;">
                                    Hi {user_name},
                                </p>
                                <p style="margin: 0 0 20px; color: #374151; font-size: 16px; line-height: 1.6;">
                                    Your account has been created successfully. You can now log in and start using the platform.
                                </p>
                                
                                {password_section}
                                
                                <!-- Button -->
                                <table role="presentation" style="width: 100%; margin: 30px 0;">
                                    <tr>
                                        <td style="text-align: center;">
                                            <a href="{login_link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px; border-radius: 8px;">
                                                Log In Now
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; background-color: #f9fafb; border-top: 1px solid #e5e7eb; border-radius: 0 0 12px 12px;">
                                <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center;">
                                    This is an automated message from {settings.APP_NAME}.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"Welcome to {settings.APP_NAME}!",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        print(f"[EMAIL] Welcome email sent to {to_email}. ID: {response.get('id', 'unknown')}")
        return True
        
    except Exception as e:
        print(f"[EMAIL] Failed to send welcome email to {to_email}: {str(e)}")
        return False
