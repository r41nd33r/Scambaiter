"""Optional live mode: poll a dedicated burner inbox over IMAP and reply over SMTP.

Use a brand-new address that is not linked to you. To plug in a different provider
(e.g. Agentboxd), implement fetch_new() and send() with the same signatures.
"""
import email
import imaplib
import logging
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr

from . import config

log = logging.getLogger(__name__)


def _text_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")


def fetch_new() -> list[dict]:
    """Returns unread messages as {sender, subject, body, message_id} and marks them read."""
    out = []
    with imaplib.IMAP4_SSL(config.IMAP_HOST) as imap:
        imap.login(config.IMAP_USER, config.IMAP_PASSWORD)
        imap.select("INBOX")
        _, data = imap.search(None, "UNSEEN")
        for num in data[0].split():
            _, raw = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(raw[0][1])
            out.append({
                "sender": parseaddr(msg.get("From", ""))[1],
                "subject": msg.get("Subject", ""),
                "body": _text_body(msg),
                "message_id": msg.get("Message-ID", ""),
            })
    return out


def send(to: str, subject: str, body: str, in_reply_to: str = ""):
    msg = EmailMessage()
    msg["From"] = config.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)
    log.info("sent reply to %s", to)
