"""Outgoing email (invitations). Locally this goes to Mailpit: open http://localhost:8025."""
import html
import logging
import smtplib
from email.message import EmailMessage

from app.core import config

logger = logging.getLogger(__name__)


def send(to: str, subject: str, text: str, html_body: str) -> bool:
    """Returns False instead of raising, so a mail outage never blocks the action itself."""
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    try:
        # local_hostname avoids a reverse-DNS lookup of this machine that can stall for seconds
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, local_hostname="yudhix-sense", timeout=10) as smtp:
            if config.SMTP_STARTTLS:
                smtp.starttls()
            if config.SMTP_USER:
                smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        logger.warning("Email to %s failed (%s). The invite link can still be copied from the Team page.", to, e)
        return False


def invitation(to: str, workspace: str, inviter: str, role: str, link: str, days: int) -> bool:
    subject = f"{inviter} invited you to {workspace} on Yudhix"
    text = (f"{inviter} invited you to join the {workspace} workspace on Yudhix as {role}.\n\n"
            f"Accept the invitation: {link}\n\nThis link expires in {days} days. "
            f"If you weren't expecting this, you can ignore this email.")
    e = html.escape
    body = f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#0f1720">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 16px">
<table role="presentation" width="100%" style="max-width:520px;background:#fff;border:1px solid #e3e6eb;border-radius:16px">
<tr><td style="padding:32px">
  <div style="font-weight:800;font-size:20px;letter-spacing:-.02em">Yudhix</div>
  <h1 style="font-size:20px;margin:24px 0 8px">Join {e(workspace)}</h1>
  <p style="color:#4a5462;line-height:1.5;margin:0 0 24px">{e(inviter)} invited you to the <strong>{e(workspace)}</strong>
     workspace as <strong>{e(role)}</strong>.</p>
  <a href="{e(link)}" style="display:inline-block;background:#4338ca;color:#fff;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:10px">Accept invitation</a>
  <p style="color:#7a8494;font-size:13px;line-height:1.5;margin:24px 0 0">This link expires in {days} days.
     If you weren't expecting this, you can ignore this email.</p>
</td></tr></table></td></tr></table></body></html>"""
    return send(to, subject, text, body)
