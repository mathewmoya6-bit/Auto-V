import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
from services.logger import logger

async def send_email(to_email: str, subject: str, html_content: str):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        
        part = MIMEText(html_content, "html")
        msg.attach(part)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

async def send_verification_email(email: str, name: str):
    html = f"""
    <html>
        <body>
            <h2>Welcome to AUTO-V!</h2>
            <p>Hi {name},</p>
            <p>Thank you for registering with AUTO-V. Please verify your email address by clicking the link below:</p>
            <p><a href="https://auto-v-frontend.onrender.com/verify.html?email={email}">Verify Email</a></p>
            <p>If you didn't create this account, please ignore this email.</p>
            <br>
            <p>Best regards,</p>
            <p><strong>AUTO-V Team</strong></p>
        </body>
    </html>
    """
    return await send_email(email, "Welcome to AUTO-V - Verify Your Email", html)

async def send_payment_receipt(email: str, name: str, amount: float, service: str):
    html = f"""
    <html>
        <body>
            <h2>Payment Receipt</h2>
            <p>Hi {name},</p>
            <p>Your payment of <strong>KES {amount:,.2f}</strong> for <strong>{service}</strong> has been successful.</p>
            <p>Thank you for using AUTO-V!</p>
            <br>
            <p><strong>AUTO-V Team</strong></p>
        </body>
    </html>
    """
    return await send_email(email, "AUTO-V - Payment Receipt", html)
