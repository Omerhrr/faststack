"""
FastStack Email Module

Provides email sending capabilities for notifications and password resets.
"""

import asyncio
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from faststack.config import settings


@dataclass
class EmailAddress:
    """Represents an email address with optional name."""
    email: str
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class EmailMessage:
    """Represents an email message."""
    subject: str
    to: list[EmailAddress]
    from_addr: EmailAddress | None = None
    reply_to: EmailAddress | None = None
    cc: list[EmailAddress] | None = None
    bcc: list[EmailAddress] | None = None
    body_text: str | None = None
    body_html: str | None = None
    attachments: list[Path] | None = None
    headers: dict[str, str] | None = None


class EmailBackend:
    """
    Email backend for sending emails via SMTP.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        use_ssl: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        """
        Initialize email backend.

        Args:
            host: SMTP server host
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Use TLS encryption
            use_ssl: Use SSL encryption
            from_email: Default from email
            from_name: Default from name
        """
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        self.username = username or settings.EMAIL_HOST_USER
        self.password = password or settings.EMAIL_HOST_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.EMAIL_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.EMAIL_USE_SSL
        self.from_email = from_email or settings.EMAIL_FROM
        self.from_name = from_name or settings.EMAIL_FROM_NAME

    def _create_message(self, email: EmailMessage) -> MIMEMultipart:
        """Create a MIME message from EmailMessage."""
        msg = MIMEMultipart("alternative")

        # Set headers
        msg["Subject"] = email.subject
        msg["From"] = str(email.from_addr or EmailAddress(self.from_email, self.from_name))
        msg["To"] = ", ".join(str(addr) for addr in email.to)

        if email.reply_to:
            msg["Reply-To"] = str(email.reply_to)

        if email.cc:
            msg["Cc"] = ", ".join(str(addr) for addr in email.cc)

        if email.bcc:
            msg["Bcc"] = ", ".join(str(addr) for addr in email.bcc)

        # Add custom headers
        if email.headers:
            for key, value in email.headers.items():
                msg[key] = value

        # Add body
        if email.body_text:
            msg.attach(MIMEText(email.body_text, "plain", "utf-8"))

        if email.body_html:
            msg.attach(MIMEText(email.body_html, "html", "utf-8"))

        # Add attachments
        if email.attachments:
            for attachment_path in email.attachments:
                if attachment_path.exists():
                    with open(attachment_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {attachment_path.name}",
                        )
                        msg.attach(part)

        return msg

    def send(self, email: EmailMessage) -> bool:
        """
        Send an email synchronously.

        Args:
            email: EmailMessage to send

        Returns:
            True if sent successfully
        """
        if not settings.EMAIL_ENABLED:
            # In development, just log the email
            print(f"[EMAIL] To: {email.to}, Subject: {email.subject}")
            return True

        msg = self._create_message(email)

        try:
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(self.host, self.port)
            else:
                smtp = smtplib.SMTP(self.host, self.port)

            if self.use_tls and not self.use_ssl:
                smtp.starttls()

            if self.username and self.password:
                smtp.login(self.username, self.password)

            recipients = [addr.email for addr in email.to]
            if email.cc:
                recipients.extend(addr.email for addr in email.cc)
            if email.bcc:
                recipients.extend(addr.email for addr in email.bcc)

            smtp.sendmail(
                self.from_email,
                recipients,
                msg.as_string(),
            )

            smtp.quit()
            return True

        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            return False

    async def send_async(self, email: EmailMessage) -> bool:
        """
        Send an email asynchronously.

        Args:
            email: EmailMessage to send

        Returns:
            True if sent successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, email)


# Global email backend instance
_email_backend: EmailBackend | None = None


def get_email_backend() -> EmailBackend:
    """Get the global email backend instance."""
    global _email_backend
    if _email_backend is None:
        _email_backend = EmailBackend()
    return _email_backend


def send_email(
    to: str | list[str] | EmailAddress | list[EmailAddress],
    subject: str,
    body_text: str | None = None,
    body_html: str | None = None,
    **kwargs,
) -> bool:
    """
    Send an email.

    Args:
        to: Recipient(s)
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body
        **kwargs: Additional EmailMessage arguments

    Returns:
        True if sent successfully
    """
    # Normalize recipients
    if isinstance(to, str):
        to = [EmailAddress(to)]
    elif isinstance(to, list) and all(isinstance(t, str) for t in to):
        to = [EmailAddress(t) for t in to]
    elif isinstance(to, EmailAddress):
        to = [to]

    email = EmailMessage(
        subject=subject,
        to=to,
        body_text=body_text,
        body_html=body_html,
        **kwargs,
    )

    backend = get_email_backend()
    return backend.send(email)


async def send_email_async(
    to: str | list[str] | EmailAddress | list[EmailAddress],
    subject: str,
    body_text: str | None = None,
    body_html: str | None = None,
    **kwargs,
) -> bool:
    """
    Send an email asynchronously.

    Args:
        to: Recipient(s)
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body
        **kwargs: Additional EmailMessage arguments

    Returns:
        True if sent successfully
    """
    # Normalize recipients
    if isinstance(to, str):
        to = [EmailAddress(to)]
    elif isinstance(to, list) and all(isinstance(t, str) for t in to):
        to = [EmailAddress(t) for t in to]
    elif isinstance(to, EmailAddress):
        to = [to]

    email = EmailMessage(
        subject=subject,
        to=to,
        body_text=body_text,
        body_html=body_html,
        **kwargs,
    )

    backend = get_email_backend()
    return await backend.send_async(email)


class EmailTemplateRenderer:
    """
    Render email templates using Jinja2.
    """

    def __init__(self, templates_dir: str | Path = "templates/emails"):
        """
        Initialize template renderer.

        Args:
            templates_dir: Directory containing email templates
        """
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, context: dict[str, Any]) -> tuple[str, str]:
        """
        Render both text and HTML versions of an email template.

        Args:
            template_name: Template name (without extension)
            context: Template context

        Returns:
            Tuple of (text_body, html_body)
        """
        text_body = ""
        html_body = ""

        # Try to render text version
        try:
            text_template = self.env.get_template(f"{template_name}.txt")
            text_body = text_template.render(**context)
        except Exception:
            pass

        # Try to render HTML version
        try:
            html_template = self.env.get_template(f"{template_name}.html")
            html_body = html_template.render(**context)
        except Exception:
            pass

        return text_body, html_body


def send_templated_email(
    to: str | list[str] | EmailAddress | list[EmailAddress],
    subject: str,
    template_name: str,
    context: dict[str, Any],
    **kwargs,
) -> bool:
    """
    Send an email using a template.

    Args:
        to: Recipient(s)
        subject: Email subject
        template_name: Template name (without extension)
        context: Template context
        **kwargs: Additional EmailMessage arguments

    Returns:
        True if sent successfully
    """
    renderer = EmailTemplateRenderer()
    body_text, body_html = renderer.render(template_name, context)

    return send_email(
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        **kwargs,
    )
