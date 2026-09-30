import random, time, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").replace(" ", "")  # strip spaces

# In-memory OTP store: { email: { "otp": "123456", "expires": timestamp } }
_otp_store: dict = {}
OTP_TTL = 600  # 10 minutes


def generate_otp(email: str) -> str:
    """Generate a 6-digit OTP, store it, and return it."""
    otp = str(random.randint(100000, 999999))
    _otp_store[email.lower()] = {
        "otp":     otp,
        "expires": time.time() + OTP_TTL
    }
    return otp


def verify_otp(email: str, otp_input: str) -> dict:
    """
    Verify the OTP for a given email.
    Returns { "success": bool, "message": str }
    """
    email = email.lower().strip()
    record = _otp_store.get(email)

    if not record:
        return {"success": False, "message": "No OTP sent to this email. Please request a new one."}

    if time.time() > record["expires"]:
        _otp_store.pop(email, None)
        return {"success": False, "message": "OTP has expired. Please request a new one."}

    if record["otp"] != otp_input.strip():
        return {"success": False, "message": "Incorrect OTP. Please try again."}

    # Valid — clear it so it can't be reused
    _otp_store.pop(email, None)
    return {"success": True, "message": "Email verified successfully!"}


def send_otp_email(email: str, otp: str) -> dict:
    """
    Send the OTP to the user's email via Gmail SMTP.
    Returns { "success": bool, "message": str }
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return {"success": False, "message": "Email service not configured."}

    subject = "BorrowLoop — Your Verification Code"
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0f0f0f;color:#f0f0f0;border-radius:12px;">
      <h2 style="color:#00c864;margin-bottom:4px;">BorrowLoop</h2>
      <p style="color:#aaa;font-size:13px;margin-top:0;">Community Sharing Marketplace</p>
      <hr style="border:1px solid #222;margin:16px 0;">
      <p style="font-size:15px;">Your verification code is:</p>
      <div style="font-size:40px;font-weight:900;letter-spacing:10px;color:#00c864;text-align:center;padding:20px 0;">{otp}</div>
      <p style="font-size:13px;color:#aaa;">This code expires in <b>10 minutes</b>. Do not share it with anyone.</p>
      <hr style="border:1px solid #222;margin:16px 0;">
      <p style="font-size:11px;color:#555;">If you did not request this, you can safely ignore this email.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"BorrowLoop <{EMAIL_SENDER}>"
    msg["To"]      = email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
        return {"success": True, "message": f"OTP sent to {email}"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Email authentication failed. Check your App Password in .env."}
    except Exception as e:
        return {"success": False, "message": f"Failed to send email: {str(e)}"}
