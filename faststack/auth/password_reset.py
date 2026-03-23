"""
FastStack Password Reset Routes

Provides password reset functionality with database-backed tokens.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from faststack.app import get_templates
from faststack.auth.models import User
from faststack.auth.utils import hash_password, validate_password_strength, get_user_by_email
from faststack.auth.permissions import (
    create_password_reset_token,
    validate_password_reset_token,
    use_password_reset_token,
    add_to_password_history,
    is_password_in_history,
)
from faststack.config import settings
from faststack.core.dependencies import DBSession
from faststack.core.responses import is_htmx
from faststack.core.session import flash
from faststack.middleware.csrf import csrf_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Render forgot password page."""
    templates = get_templates()
    
    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {
            "request": request,
            "title": "Forgot Password",
            "csrf_token": csrf_token(request),
        },
    )


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    session: DBSession,
    email: str = Form(...),
):
    """
    Handle forgot password form submission.
    
    Always returns success message even if email doesn't exist
    to prevent email enumeration.
    """
    # Get client info for audit
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Check if user exists
    user = get_user_by_email(session, email)
    
    if user and user.is_active:
        # Create reset token
        token = create_password_reset_token(
            session=session,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # In production, send email with reset link
        # For now, just log it
        reset_url = f"{request.url.scheme}://{request.url.netloc}/auth/reset-password/{token.token}"
        print(f"[PASSWORD RESET] Reset URL for {email}: {reset_url}")
        
        # TODO: Send email with reset link
        # await send_password_reset_email(user.email, reset_url)
    
    # Always return success to prevent email enumeration
    if is_htmx(request):
        return HTMLResponse(
            content='<div class="alert alert-success">If an account exists with that email, you will receive a password reset link.</div>'
        )
    
    flash(request, "If an account exists with that email, you will receive a password reset link.", "info")
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    session: DBSession,
):
    """Render reset password page."""
    templates = get_templates()
    
    # Validate token
    user = validate_password_reset_token(session, token)
    
    if not user:
        return templates.TemplateResponse(
            "auth/reset_password_invalid.html",
            {
                "request": request,
                "title": "Invalid Token",
            },
        )
    
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {
            "request": request,
            "title": "Reset Password",
            "token": token,
            "csrf_token": csrf_token(request),
        },
    )


@router.post("/reset-password/{token}")
async def reset_password(
    request: Request,
    token: str,
    session: DBSession,
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    """Handle reset password form submission."""
    # Validate token
    user = validate_password_reset_token(session, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Validate password match
    if password != password_confirm:
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Passwords do not match</div>',
                status_code=400,
            )
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(url=f"/auth/reset-password/{token}", status_code=302)
    
    # Validate password strength
    is_valid, errors = validate_password_strength(password)
    if not is_valid:
        error_msg = ". ".join(errors)
        if is_htmx(request):
            return HTMLResponse(
                content=f'<div class="alert alert-error">{error_msg}</div>',
                status_code=400,
            )
        flash(request, error_msg, "error")
        return RedirectResponse(url=f"/auth/reset-password/{token}", status_code=302)
    
    # Check password history
    if is_password_in_history(session, user, password):
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Cannot reuse a recent password</div>',
                status_code=400,
            )
        flash(request, "Cannot reuse a recent password", "error")
        return RedirectResponse(url=f"/auth/reset-password/{token}", status_code=302)
    
    # Add old password to history
    add_to_password_history(session, user, user.password_hash)
    
    # Update password
    user.password_hash = hash_password(password)
    session.add(user)
    
    # Mark token as used
    use_password_reset_token(session, token)
    
    session.commit()
    
    if is_htmx(request):
        return HTMLResponse(
            content='<div class="alert alert-success">Password reset successfully. You can now log in.</div>'
        )
    
    flash(request, "Password reset successfully. You can now log in.", "success")
    return RedirectResponse(url="/auth/login", status_code=302)
