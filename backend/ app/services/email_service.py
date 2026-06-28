# app/services/email_service.py (FULLY UPDATED FOR JINJA2 3.1.4)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from datetime import datetime
import jinja2

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Production email service with Jinja2 3.1.4 template support"""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.tls = settings.SMTP_TLS
        self.base_url = settings.BASE_URL
        
        # Setup Jinja2 environment for templates
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        
        # Ensure template directory exists
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Jinja2 with autoescape and optimized settings
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
            cache_size=50,  # Cache up to 50 templates
            auto_reload=False  # Disable auto-reload in production
        )
        
        # Add custom filters
        self.jinja_env.filters['format_currency'] = self.format_currency
        self.jinja_env.filters['format_date'] = self.format_date
        self.jinja_env.filters['truncate_text'] = self.truncate_text
        self.jinja_env.globals['now'] = datetime.utcnow
        
        logger.info(f"Email service initialized with templates from: {template_dir}")
    
    @staticmethod
    def format_currency(value):
        """Format currency values (KES)"""
        if value is None:
            return "0.00"
        try:
            return f"KES {float(value):,.2f}"
        except (ValueError, TypeError):
            return f"KES {value}"
    
    @staticmethod
    def format_date(value, format_str="%B %d, %Y"):
        """Format datetime objects"""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(value, datetime):
            return value.strftime(format_str)
        return str(value)
    
    @staticmethod
    def truncate_text(value, length=100, suffix="..."):
        """Truncate text to specified length"""
        if not value:
            return ""
        if len(value) <= length:
            return value
        return value[:length].rsplit(' ', 1)[0] + suffix
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> bool:
        """
        Send an email using Jinja2 template
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Name of template file (e.g., 'verification.html')
            context: Template context variables
            from_email: Sender email (optional)
            cc: CC recipient (optional)
            bcc: BCC recipient (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Validate template exists
            if not self._template_exists(template_name):
                logger.error(f"Template not found: {template_name}")
                return False
            
            # Add base context
            base_context = {
                'base_url': self.base_url,
                'support_email': settings.SMTP_FROM_EMAIL,
                'current_year': datetime.utcnow().year,
                'current_date': datetime.utcnow().isoformat()
            }
            
            # Merge contexts (base_context gets overridden by provided context)
            full_context = {**base_context, **context}
            
            # Render template
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**full_context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.from_email
            msg['To'] = to_email
            
            if cc:
                msg['Cc'] = cc
            if bcc:
                msg['Bcc'] = bcc
            
            # Add plain text version (extract text from HTML)
            plain_text = self._html_to_text(html_content)
            msg.attach(MIMEText(plain_text, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            recipients = [to_email]
            if cc:
                recipients.append(cc)
            if bcc:
                recipients.append(bcc)
            
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to: {to_email} - Subject: {subject}")
            return True
            
        except jinja2.TemplateNotFound as e:
            logger.error(f"Template not found: {template_name} - {str(e)}")
            return False
        except jinja2.TemplateError as e:
            logger.error(f"Template error in {template_name}: {str(e)}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def _template_exists(self, template_name: str) -> bool:
        """Check if template file exists"""
        try:
            self.jinja_env.get_template(template_name)
            return True
        except jinja2.TemplateNotFound:
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simple implementation)"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove &nbsp; and other entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # Clean up newlines
        text = text.strip()
        return text

    # ============================================
    # SPECIFIC EMAIL METHODS
    # ============================================
    
    async def send_verification_email(self, to_email: str, name: str, token: str) -> bool:
        """Send email verification email"""
        verification_url = f"{self.base_url}/api/v1/auth/verify-email?token={token}"
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
    
    async def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Send welcome email"""
        return await self.send_email(
            to_email=to_email,
            subject="Welcome to AUTO-V! 🚗",
            template_name="welcome.html",
            context={'name': name}
        )
    
    async def send_password_reset_email(self, to_email: str, name: str, token: str) -> bool:
        """Send password reset email"""
        reset_url = f"{self.base_url}/reset-password?token={token}"
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
    
    async def send_valuation_complete_email(
        self, 
        to_email: str, 
        name: str, 
        valuation_data: Dict[str, Any]
    ) -> bool:
        """Send valuation complete email"""
        return await self.send_email(
            to_email=to_email,
            subject="Valuation Complete - AUTO-V 📊",
            template_name="valuation_complete.html",
            context={'name': name, **valuation_data}
        )
    
    async def send_valuation_ready_email(
        self, 
        to_email: str, 
        name: str, 
        report_data: Dict[str, Any]
    ) -> bool:
        """Send valuation ready email"""
        return await self.send_email(
            to_email=to_email,
            subject="Your Valuation Report is Ready - AUTO-V 📄",
            template_name="valuation_ready.html",
            context={'name': name, **report_data}
        )
    
    async def send_report_ready_email(
        self, 
        to_email: str, 
        name: str, 
        report_data: Dict[str, Any]
    ) -> bool:
        """Send report ready email"""
        return await self.send_email(
            to_email=to_email,
            subject="Your Report is Ready for Download - AUTO-V 📥",
            template_name="report_ready.html",
            context={'name': name, **report_data}
        )
    
    async def send_payment_receipt_email(
        self, 
        to_email: str, 
        name: str, 
        payment_data: Dict[str, Any]
    ) -> bool:
        """Send payment receipt email"""
        return await self.send_email(
            to_email=to_email,
            subject="Payment Receipt - AUTO-V 💳",
            template_name="payment_receipt.html",
            context={'name': name, **payment_data}
        )
    
    async def send_quotation_email(
        self, 
        to_email: str, 
        name: str, 
        quotation_data: Dict[str, Any]
    ) -> bool:
        """Send quotation email"""
        return await self.send_email(
            to_email=to_email,
            subject="Vehicle Quotation - AUTO-V 📋",
            template_name="quotation.html",
            context={'name': name, **quotation_data}
        )
    
    async def send_invoice_email(
        self, 
        to_email: str, 
        name: str, 
        invoice_data: Dict[str, Any]
    ) -> bool:
        """Send invoice email"""
        invoice_number = invoice_data.get('invoice_number', '')
        return await self.send_email(
            to_email=to_email,
            subject=f"Invoice #{invoice_number} - AUTO-V 🧾",
            template_name="invoice.html",
            context={'name': name, **invoice_data}
        )
    
    async def send_account_locked_email(
        self, 
        to_email: str, 
        name: str, 
        lock_data: Dict[str, Any]
    ) -> bool:
        """Send account locked email"""
        return await self.send_email(
            to_email=to_email,
            subject="Account Locked - AUTO-V 🔒",
            template_name="account_locked.html",
            context={'name': name, **lock_data}
        )
    
    async def send_login_alert_email(
        self, 
        to_email: str, 
        name: str, 
        login_data: Dict[str, Any]
    ) -> bool:
        """Send login alert email"""
        return await self.send_email(
            to_email=to_email,
            subject="New Login Detected - AUTO-V 🔔",
            template_name="login_alert.html",
            context={'name': name, **login_data}
        )
    
    async def send_email_changed_email(
        self, 
        to_email: str, 
        name: str, 
        change_data: Dict[str, Any]
    ) -> bool:
        """Send email changed email"""
        return await self.send_email(
            to_email=to_email,
            subject="Email Address Changed - AUTO-V 📧",
            template_name="email_changed.html",
            context={'name': name, **change_data}
        )
    
    async def send_subscription_expiry_email(
        self, 
        to_email: str, 
        name: str, 
        expiry_data: Dict[str, Any]
    ) -> bool:
        """Send subscription expiry email"""
        return await self.send_email(
            to_email=to_email,
            subject="Subscription Expiring Soon - AUTO-V ⏰",
            template_name="subscription_expiry.html",
            context={'name': name, **expiry_data}
        )

# Singleton instance
email_service = EmailService()
