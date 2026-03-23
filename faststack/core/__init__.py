"""
FastStack Core Module

Provides core utilities and helpers.
"""

from faststack.core.dependencies import get_current_user, get_optional_user, CurrentUser, OptionalUser, AdminUser, DBSession
from faststack.core.responses import HTMXResponse, redirect, is_htmx
from faststack.core.session import SessionManager, get_session_data, flash, get_flashes, login_user, logout_user
from faststack.core.signals import signal_manager, SignalType, receiver
from faststack.core.email import send_email, send_email_async, send_templated_email, EmailAddress, EmailMessage
from faststack.core.uploads import upload_file, delete_file, FileUploader, UploadedFile

__all__ = [
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "CurrentUser",
    "OptionalUser",
    "AdminUser",
    "DBSession",
    # Responses
    "HTMXResponse",
    "redirect",
    "is_htmx",
    # Session
    "SessionManager",
    "get_session_data",
    "flash",
    "get_flashes",
    "login_user",
    "logout_user",
    # Signals
    "signal_manager",
    "SignalType",
    "receiver",
    # Email
    "send_email",
    "send_email_async",
    "send_templated_email",
    "EmailAddress",
    "EmailMessage",
    # Uploads
    "upload_file",
    "delete_file",
    "FileUploader",
    "UploadedFile",
]
