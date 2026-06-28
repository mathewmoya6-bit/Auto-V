# app/services/email_service.py (UPDATED with all template methods)
from pathlib import Path
import jinja2
from typing import Dict, Any, Optional
import logging

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
        self.base_url = settings.BASE_URL
        
        # Setup Jinja2 environment for templates
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True
        )
        
        # Add custom filters
        self.jinja_env.filters['format_currency'] = self.format_currency
    
    @staticmethod
    def format_currency(value):
        """Format currency values"""
        if value is None:
            return "0.00"
        return f"{value:,.2f}"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None
    ) -> bool:
        """Send an email using template"""
        try:
            # Add base context
            context.update({
                'base_url': self.base_url,
                'support_email': settings.SMTP_FROM_EMAIL,
                'year': datetime.utcnow().year
            })
            
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
    
    # All specific email methods...
    async def send_verification_email(self, to_email: str, name: str, token: str):
        url = f"{self.base_url}/api/v1/auth/verify-email?token={token}"
        return await self.send_email(
            to_email=to_email,
            subject="Verify Your Email - AUTO-V",
            template_name="verification.html",
            context={'name': name, 'verification_url': url, 'expires_in': '24 hours'}
        )
    
    async def send_welcome_email(self, to_email: str, name: str):
        return await self.send_email(
            to_email=to_email,
            subject="Welcome to AUTO-V!",
            template_name="welcome.html",
            context={'name': name}
        )
    
    async def send_password_reset_email(self, to_email: str, name: str, token: str):
        url = f"{self.base_url}/reset-password?token={token}"
        return await self.send_email(
            to_email=to_email,
            subject="Password Reset - AUTO-V",
            template_name="password_reset.html",
            context={'name': name, 'reset_url': url, 'expires_in': '1 hour'}
        )
    
    async def send_valuation_complete_email(self, to_email: str, name: str, valuation_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Valuation Complete - AUTO-V",
            template_name="valuation_complete.html",
            context={
                'name': name,
                **valuation_data
            }
        )
    
    async def send_valuation_ready_email(self, to_email: str, name: str, report_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Your Valuation Report is Ready - AUTO-V",
            template_name="valuation_ready.html",
            context={
                'name': name,
                **report_data
            }
        )
    
    async def send_report_ready_email(self, to_email: str, name: str, report_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Your Report is Ready for Download - AUTO-V",
            template_name="report_ready.html",
            context={
                'name': name,
                **report_data
            }
        )
    
    async def send_payment_receipt_email(self, to_email: str, name: str, payment_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Payment Receipt - AUTO-V",
            template_name="payment_receipt.html",
            context={
                'name': name,
                **payment_data
            }
        )
    
    async def send_quotation_email(self, to_email: str, name: str, quotation_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Vehicle Quotation - AUTO-V",
            template_name="quotation.html",
            context={
                'name': name,
                **quotation_data
            }
        )
    
    async def send_invoice_email(self, to_email: str, name: str, invoice_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject=f"Invoice #{invoice_data.get('invoice_number')} - AUTO-V",
            template_name="invoice.html",
            context={
                'name': name,
                **invoice_data
            }
        )
    
    async def send_account_locked_email(self, to_email: str, name: str, lock_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Account Locked - AUTO-V",
            template_name="account_locked.html",
            context={
                'name': name,
                **lock_data
            }
        )
    
    async def send_login_alert_email(self, to_email: str, name: str, login_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="New Login Detected - AUTO-V",
            template_name="login_alert.html",
            context={
                'name': name,
                **login_data
            }
        )
    
    async def send_email_changed_email(self, to_email: str, name: str, change_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Email Address Changed - AUTO-V",
            template_name="email_changed.html",
            context={
                'name': name,
                **change_data
            }
        )
    
    async def send_subscription_expiry_email(self, to_email: str, name: str, expiry_data: Dict):
        return await self.send_email(
            to_email=to_email,
            subject="Subscription Expiring Soon - AUTO-V",
            template_name="subscription_expiry.html",
            context={
                'name': name,
                **expiry_data
            }
        )
