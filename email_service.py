import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import logging
from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for verification and password reset
    """
    
    @staticmethod
    def generate_verification_code() -> str:
        """Generate 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def send_email(to_email: str, subject: str, html_body: str) -> bool:
        """
        Send email using SMTP
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML content
        
        Returns:
            True if sent successfully, False otherwise
        """
        
        if not settings.EMAIL_ENABLED:
            logger.warning("📧 Email disabled in settings")
            print(f"\n{'='*60}")
            print(f"📧 EMAIL (Not Sent - Email Disabled)")
            print(f"{'='*60}")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"{'='*60}\n")
            return False
        
        if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
            logger.error("❌ Email credentials not configured")
            print(f"\n{'='*60}")
            print(f"⚠️  EMAIL NOT SENT - Configure EMAIL_USER and EMAIL_PASSWORD in .env")
            print(f"{'='*60}")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"{'='*60}\n")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server
            print(f"📧 Connecting to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            # Login
            print(f"🔐 Logging in as {settings.EMAIL_USER}...")
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            
            # Send email
            print(f"📤 Sending email to {to_email}...")
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to {to_email}")
            logger.info(f"Email sent to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP Authentication failed - Check EMAIL_USER and EMAIL_PASSWORD")
            print("\n" + "="*60)
            print("❌ EMAIL AUTHENTICATION FAILED")
            print("="*60)
            print("Please check:")
            print("1. EMAIL_USER is correct")
            print("2. EMAIL_PASSWORD is a Gmail App Password (not your regular password)")
            print("3. 2-Factor Authentication is enabled on your Google Account")
            print("4. Generate App Password at: https://myaccount.google.com/apppasswords")
            print("="*60 + "\n")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            print(f"\n❌ Email sending failed: {e}\n")
            return False
            
        except Exception as e:
            logger.error(f"❌ Email error: {e}")
            print(f"\n❌ Unexpected error: {e}\n")
            return False
        
    @staticmethod
    def send_password_reset_email(to_email: str, reset_code: str, username: str = "User") -> bool:
        """Send password reset code email"""
        
        subject = "NeuroLens - Password Reset Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background: linear-gradient(135deg, #E57373 0%, #C62828 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .code-box {{
                    background-color: #ffebee;
                    border: 2px dashed #E57373;
                    padding: 20px;
                    text-align: center;
                    font-size: 32px;
                    font-weight: bold;
                    color: #E57373;
                    letter-spacing: 5px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset</h1>
                    <p>NeuroLens</p>
                </div>
                <div class="content">
                    <h2>Hello, {username}!</h2>
                    <p>We received a request to reset your password. Use the code below to proceed:</p>
                    
                    <div class="code-box">
                        {reset_code}
                    </div>
                    
                    <p><strong>This code will expire in 10 minutes.</strong></p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Note:</strong> If you didn't request this password reset, please ignore this email and secure your account.
                    </div>
                    
                    <div class="footer">
                        <p>© 2025 NeuroLens. All rights reserved.</p>
                        <p>This is an automated message, please do not reply.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(to_email, subject, html_body)
    
    
    @staticmethod
    def send_verification_email(to_email: str, verification_code: str, username: str = "User") -> bool:
        """Send email verification code"""
        
        subject = "NeuroLens - Verify Your Email"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background: linear-gradient(135deg, #4DB6AC 0%, #3D9B93 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .code-box {{
                    background-color: #e0f2f1;
                    border: 2px dashed #4DB6AC;
                    padding: 20px;
                    text-align: center;
                    font-size: 32px;
                    font-weight: bold;
                    color: #4DB6AC;
                    letter-spacing: 5px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .info {{
                    background-color: #e3f2fd;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✉️ Verify Your Email</h1>
                    <p>NeuroLens</p>
                </div>
                <div class="content">
                    <h2>Hello, {username}!</h2>
                    <p>Thank you for signing up for NeuroLens. Please verify your email address using the code below:</p>
                    
                    <div class="code-box">
                        {verification_code}
                    </div>
                    
                    <p><strong>This code will expire in 10 minutes.</strong></p>
                    
                    <div class="info">
                        <strong>ℹ️ What's Next:</strong> Once verified, you'll be able to access all NeuroLens features including emotion tracking, session recording, and weekly analytics.
                    </div>
                    
                    <p>If you didn't create an account with NeuroLens, please ignore this email.</p>
                    
                    <div class="footer">
                        <p>© 2025 NeuroLens. All rights reserved.</p>
                        <p>This is an automated message, please do not reply.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(to_email, subject, html_body)
    
    @staticmethod
    def send_welcome_email(to_email: str, username: str) -> bool:
        """Send welcome email after successful verification"""
        
        subject = "Welcome to NeuroLens! 🎉"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background: linear-gradient(135deg, #4DB6AC 0%, #3D9B93 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .feature {{
                    margin: 15px 0;
                    padding-left: 30px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to NeuroLens!</h1>
                </div>
                <div class="content">
                    <h2>Hi {username}!</h2>
                    <p>Your email has been verified successfully. You're all set to start monitoring your mental well-being!</p>
                    
                    <h3>What you can do with NeuroLens:</h3>
                    <div class="feature">📹 Record sessions with camera-only (no audio)</div>
                    <div class="feature">😊 Real-time emotion detection</div>
                    <div class="feature">📊 Weekly reports and analytics</div>
                    <div class="feature">💡 Personalized recommendations</div>
                    <div class="feature">🔒 Secure, encrypted data storage</div>
                    
                    <p style="margin-top: 30px;">Ready to get started? Log in to your account and begin your first session!</p>
                    
                    <div class="footer">
                        <p>© 2025 NeuroLens. All rights reserved.</p>
                        <p>Need help? Contact us at support@neurolens.app</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(to_email, subject, html_body)


# Test email service
if __name__ == "__main__":
    print("🧪 Testing Email Service\n")
    
    test_email = input("Enter your email to test: ").strip()
    
    if test_email:
        code = EmailService.generate_verification_code()
        print(f"\nSending test verification email to {test_email}...")
        print(f"Code: {code}\n")
        
        success = EmailService.send_verification_email(test_email, code, "Test User")
        
        if success:
            print("\n✅ Test email sent successfully!")
            print("Check your inbox (and spam folder)")
        else:
            print("\n❌ Failed to send test email")
            print("Check the error messages above")
    else:
        print("No email provided")