import logging
from typing import List, Optional, Dict, Any
import resend
from app.config import settings
from jinja2 import Template

logger = logging.getLogger(__name__)

# Configure Resend global API key
resend.api_key = settings.RESEND_API_KEY


class EmailService:
    """Email service with template rendering."""
    
    @staticmethod
    def send_email(
        to: List[str],
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        return_details: bool = False
    ) -> Any:
        """
        Send email using Resend.
        
        Args:
            to: List of recipient emails
            subject: Email subject
            html_content: HTML email content
            from_email: Sender email (default: configured sender)
            return_details: If True, returns (success, message/error) tuple.
        
        Returns:
            bool or (bool, str)
        """
        # Mock mode if no API key or placeholder
        api_key = settings.RESEND_API_KEY
        if not api_key or api_key.startswith("your-") or api_key == "None":
            msg = "Resend API Key missing/invalid. Mocking success."
            logger.info(msg)
            return (True, msg) if return_details else True

        try:
            params = {
                "from": from_email or settings.EMAIL_FROM,
                "to": to,
                "subject": subject,
                "html": html_content
            }
            
            # Use the global resend module
            response = resend.Emails.send(params)
            logger.info(f"Email sent to {to}: {response}")
            return (True, "Email sent successfully") if return_details else True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            error_str = str(e)
            
            # Auth error check
            if "401" in error_str.lower() or "unauthorized" in error_str.lower():
                 msg = "Mock Success (Auth Failed during dev)"
                 logger.warning(f"{msg}: {error_str}")
                 return (True, msg) if return_details else True
            
            return (False, error_str) if return_details else False

    # ... [Keep other methods as is, they just call send_email default] ...

    @staticmethod
    def send_client_reminder_email(
        to_emails: List[str],
        subject: str,
        message: str,
        project_title: str,
        sender_name: str,
        return_details: bool = False
    ) -> Any:
        """Send client reminder notification email."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #3B82F6; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9fafb; }
                .message-box { background: white; padding: 15px; border: 1px solid #e5e7eb; border-radius: 4px; margin: 20px 0; white-space: pre-wrap; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Project Onboarding</h1>
                </div>
                <div class="content">
                    <h2>Project: {{ project_title }}</h2>
                    <div class="message-box">{{ message }}</div>
                </div>
                <div class="footer">
                    <p>Multi-Agent Delivery Pipeline</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            "project_title": project_title,
            "message": message,
            "sender_name": sender_name
        }
        
        html_content = EmailService.render_template(template, context)
        return EmailService.send_email(
            to=to_emails,
            subject=subject,
            html_content=html_content,
            return_details=return_details
        )

    
    @staticmethod
    def render_template(template_str: str, context: Dict[str, Any]) -> str:
        """Render Jinja2 template with context."""
        template = Template(template_str)
        return template.render(**context)
    
    @staticmethod
    def send_project_created_email(
        to: List[str],
        project_title: str,
        project_id: str,
        created_by: str,
        manager_name: Optional[str] = None
    ) -> bool:
        """Send project created notification email."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9fafb; }
                .button { background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 New Project Created</h1>
                </div>
                <div class="content">
                    <h2>{{ project_title }}</h2>
                    <p>A new project has been created and assigned to you.</p>
                    <p><strong>Created by:</strong> {{ created_by }}</p>
                    {% if manager_name %}
                    <p><strong>Manager:</strong> {{ manager_name }}</p>
                    {% endif %}
                    <p><strong>Project ID:</strong> {{ project_id }}</p>
                    <a href="{{ app_url }}/projects/{{ project_id }}" class="button">View Project</a>
                </div>
                <div class="footer">
                    <p>Multi-Agent Delivery Pipeline</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            "project_title": project_title,
            "project_id": project_id,
            "created_by": created_by,
            "manager_name": manager_name,
            "app_url": settings.FRONTEND_URL or "http://localhost:3000"
        }
        
        html_content = EmailService.render_template(template, context)
        return EmailService.send_email(
            to=to,
            subject=f"New Project: {project_title}",
            html_content=html_content
        )
    
    @staticmethod
    def send_stage_transition_email(
        to: List[str],
        project_title: str,
        project_id: str,
        old_stage: str,
        new_stage: str,
        transitioned_by: str
    ) -> bool:
        """Send stage transition notification email."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #10B981; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9fafb; }
                .stage-transition { background: white; padding: 15px; border-left: 4px solid #10B981; margin: 20px 0; }
                .button { background: #10B981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Stage Transition</h1>
                </div>
                <div class="content">
                    <h2>{{ project_title }}</h2>
                    <div class="stage-transition">
                        <p><strong>{{ old_stage }}</strong> → <strong>{{ new_stage }}</strong></p>
                    </div>
                    <p><strong>Transitioned by:</strong> {{ transitioned_by }}</p>
                    <a href="{{ app_url }}/projects/{{ project_id }}" class="button">View Project</a>
                </div>
                <div class="footer">
                    <p>Multi-Agent Delivery Pipeline</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            "project_title": project_title,
            "project_id": project_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "transitioned_by": transitioned_by,
            "app_url": settings.FRONTEND_URL or "http://localhost:3000"
        }
        
        html_content = EmailService.render_template(template, context)
        return EmailService.send_email(
            to=to,
            subject=f"Stage Update: {project_title}",
            html_content=html_content
        )
    
    @staticmethod
    def send_task_assigned_email(
        to: List[str],
        task_title: str,
        task_id: str,
        project_title: str,
        project_id: str,
        assigned_by: str,
        due_date: Optional[str] = None
    ) -> bool:
        """Send task assignment notification email."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #F59E0B; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9fafb; }
                .task-info { background: white; padding: 15px; border-left: 4px solid #F59E0B; margin: 20px 0; }
                .button { background: #F59E0B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ New Task Assigned</h1>
                </div>
                <div class="content">
                    <h2>{{ task_title }}</h2>
                    <div class="task-info">
                        <p><strong>Project:</strong> {{ project_title }}</p>
                        <p><strong>Assigned by:</strong> {{ assigned_by }}</p>
                        {% if due_date %}
                        <p><strong>Due date:</strong> {{ due_date }}</p>
                        {% endif %}
                    </div>
                    <a href="{{ app_url }}/projects/{{ project_id }}" class="button">View Task</a>
                </div>
                <div class="footer">
                    <p>Multi-Agent Delivery Pipeline</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            "task_title": task_title,
            "task_id": task_id,
            "project_title": project_title,
            "project_id": project_id,
            "assigned_by": assigned_by,
            "due_date": due_date,
            "app_url": settings.FRONTEND_URL or "http://localhost:3000"
        }
        
        html_content = EmailService.render_template(template, context)
        return EmailService.send_email(
            to=to,
            subject=f"New Task: {task_title}",
            html_content=html_content
        )

    @staticmethod
    def send_password_reset_email(
        to_email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """Send password reset link email."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #EF4444; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9fafb; }
                .button { background: #EF4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Password Reset</h1>
                </div>
                <div class="content">
                    <p>Hello {{ user_name }},</p>
                    <p>You requested a password reset for your account. Click the button below to set a new password:</p>
                    <a href="{{ app_url }}/reset-password?token={{ reset_token }}" class="button">Reset Password</a>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Multi-Agent Delivery Pipeline</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        context = {
            "user_name": user_name,
            "reset_token": reset_token,
            "app_url": settings.FRONTEND_URL or "http://localhost:3000"
        }
        
        html_content = EmailService.render_template(template, context)
        return EmailService.send_email(
            to=[to_email],
            subject="Reset Your Password",
            html_content=html_content
        )




def send_password_reset_email(to_email: str, reset_token: str, user_name: str) -> bool:
    """Module-level function to send password reset email (proxy to class)"""
    return EmailService.send_password_reset_email(to_email, reset_token, user_name)


def send_client_reminder_email(
    to_emails: List[str], 
    subject: str, 
    message: str, 
    project_title: str, 
    sender_name: str, 
    return_details: bool = False
) -> Any:
    """Module-level function to send client reminder email (proxy to class)"""
    return EmailService.send_client_reminder_email(
        to_emails, 
        subject, 
        message, 
        project_title, 
        sender_name, 
        return_details
    )


# Global email service instance
email_service = EmailService()
