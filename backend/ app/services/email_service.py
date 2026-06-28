# app/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import jinja2

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Production email service with template support"""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.tls = settings.SMTP_TLS
        
        # Setup Jinja2 environment for templates
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True
        )
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None
    ) -> bool:
        """Send an email using Jinja2 template"""
        try:
            # Render template
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.from_email
            msg['To'] = to_email
            
            # Attach HTML
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent to: {to_email} - Subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        name: str,
        verification_url: str
    ) -> bool:
        """Send email verification email"""
        return await self.send_email(
            to_email=to_email,
            subject="Verify Your Email - AUTO-V",
            template_name="verification.html",
            context={
                'name': name,
                'verification_url': verification_url,
                'expires_in': '24 hours'
            }
        )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        name: str,
        reset_url: str
    ) -> bool:
        """Send password reset email"""
        return await self.send_email(
            to_email=to_email,
            subject="Password Reset - AUTO-V",
            template_name="password_reset.html",
            context={
                'name': name,
                'reset_url': reset_url,
                'expires_in': '1 hour'
            }
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """Send welcome email"""
        return await self.send_email(
            to_email=to_email,
            subject="Welcome to AUTO-V!",
            template_name="welcome.html",
            context={
                'name': name,
                'support_email': settings.SMTP_FROM_EMAIL
            }
        )
