"""
FastStack Authentication Routes

Provides login, logout, and registration routes with brute force protection.
"""

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from faststack.app import get_templates
from faststack.auth.models import User, UserCreate, UserLogin, UserRead
from faststack.auth.utils import (
    authenticate_user,
    create_user,
    get_user_by_email,
    hash_password,
    validate_password_strength,
    is_account_locked,
    get_failed_attempts,
    get_lockout_remaining,
    get_progressive_delay,
)
from faststack.config import settings
from faststack.core.dependencies import CurrentUser, DBSession, get_current_user
from faststack.core.session import flash, login_user, logout_user, is_authenticated
from faststack.core.responses import is_htmx, HTMXResponse
from faststack.middleware.csrf import csrf_token

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """Get client IP address, respecting trusted proxies."""
    # Check X-Forwarded-For if trusted proxies are configured
    if settings.RATE_LIMIT_TRUSTED_PROXIES:
        client_host = request.client.host if request.client else ""
        
        # Check if request comes from trusted proxy
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for and client_host in settings.RATE_LIMIT_TRUSTED_PROXIES:
            # Get the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    templates = get_templates()
    
    # Generate CSRF token
    token = csrf_token(request)
    
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "title": "Login",
            "csrf_token": token,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    session: DBSession,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token_value: str = Form(None, alias="csrf_token"),
):
    """
    Handle login form submission.

    Supports both regular form submission and HTMX requests.
    Includes brute force protection.
    """
    client_ip = get_client_ip(request)
    
    # Check if account is locked (by email or IP)
    if is_account_locked(email):
        remaining = get_lockout_remaining(email)
        if is_htmx(request):
            return HTMLResponse(
                content=f'<div class="alert alert-error">Account temporarily locked. Try again in {remaining} seconds.</div>',
                status_code=429,
            )
        flash(request, f"Account temporarily locked. Try again in {remaining} seconds.", "error")
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check IP-based lockout
    if is_account_locked(client_ip):
        remaining = get_lockout_remaining(client_ip)
        if is_htmx(request):
            return HTMLResponse(
                content=f'<div class="alert alert-error">Too many failed attempts from your IP. Try again in {remaining} seconds.</div>',
                status_code=429,
            )
        flash(request, f"Too many failed attempts. Try again in {remaining} seconds.", "error")
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user = authenticate_user(session, email, password)

    if not user:
        # Add progressive delay if enabled
        if settings.BRUTE_FORCE_PROGRESSIVE_DELAY:
            delay = get_progressive_delay(email)
            if delay > 0:
                time.sleep(delay)
        
        if is_htmx(request):
            attempts_left = settings.BRUTE_FORCE_MAX_ATTEMPTS - get_failed_attempts(email)
            msg = "Invalid email or password"
            if attempts_left > 0:
                msg += f" ({attempts_left} attempts remaining)"
            else:
                msg = "Account locked due to too many failed attempts"
            return HTMLResponse(
                content=f'<div class="alert alert-error">{msg}</div>',
                status_code=401,
            )
        flash(request, "Invalid email or password", "error")
        return RedirectResponse(url="/auth/login", status_code=302)

    if not user.is_active:
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Account is disabled</div>',
                status_code=403,
            )
        flash(request, "Account is disabled", "error")
        return RedirectResponse(url="/auth/login", status_code=302)

    # Log user in (with session regeneration)
    login_user(request, user.id, email=user.email)

    if is_htmx(request):
        return HTMXResponse.redirect("/admin/")

    flash(request, f"Welcome back, {user.display_name}!", "success")
    return RedirectResponse(url="/admin/", status_code=302)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render registration page."""
    templates = get_templates()
    
    # Generate CSRF token
    token = csrf_token(request)
    
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "title": "Register",
            "csrf_token": token,
        },
    )


@router.post("/register")
async def register(
    request: Request,
    session: DBSession,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    csrf_token_value: str = Form(None, alias="csrf_token"),
):
    """
    Handle registration form submission.
    """
    # Validate password match
    if password != password_confirm:
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Passwords do not match</div>',
                status_code=400,
            )
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(url="/auth/register", status_code=302)

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
        return RedirectResponse(url="/auth/register", status_code=302)

    # Check if user exists
    existing_user = get_user_by_email(session, email)
    if existing_user:
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Email already registered</div>',
                status_code=400,
            )
        flash(request, "Email already registered", "error")
        return RedirectResponse(url="/auth/register", status_code=302)

    # Create user
    user = create_user(
        session,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    # Log user in (with session regeneration)
    login_user(request, user.id, email=user.email)

    if is_htmx(request):
        return HTMXResponse.redirect("/admin/")

    flash(request, "Account created successfully!", "success")
    return RedirectResponse(url="/admin/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    logout_user(request)
    flash(request, "You have been logged out", "info")
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: CurrentUser):
    """Render profile page."""
    templates = get_templates()
    
    # Generate CSRF token
    token = csrf_token(request)
    
    return templates.TemplateResponse(
        "auth/profile.html",
        {
            "request": request,
            "title": "Profile",
            "user": user,
            "csrf_token": token,
        },
    )


@router.post("/profile")
async def update_profile(
    request: Request,
    session: DBSession,
    user: CurrentUser,
    first_name: str = Form(None),
    last_name: str = Form(None),
    csrf_token_value: str = Form(None, alias="csrf_token"),
):
    """Update user profile."""
    user.first_name = first_name
    user.last_name = last_name
    session.add(user)
    session.commit()

    if is_htmx(request):
        return HTMLResponse(
            content='<div class="alert alert-success">Profile updated</div>'
        )

    flash(request, "Profile updated", "success")
    return RedirectResponse(url="/auth/profile", status_code=302)


@router.post("/change-password")
async def change_password(
    request: Request,
    session: DBSession,
    user: CurrentUser,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    csrf_token_value: str = Form(None, alias="csrf_token"),
):
    """Change user password."""
    from faststack.auth.utils import verify_password, hash_password

    # Verify current password
    if not verify_password(current_password, user.password_hash):
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Current password is incorrect</div>',
                status_code=400,
            )
        flash(request, "Current password is incorrect", "error")
        return RedirectResponse(url="/auth/profile", status_code=302)

    # Validate password match
    if new_password != new_password_confirm:
        if is_htmx(request):
            return HTMLResponse(
                content='<div class="alert alert-error">Passwords do not match</div>',
                status_code=400,
            )
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(url="/auth/profile", status_code=302)

    # Validate password strength
    is_valid, errors = validate_password_strength(new_password)
    if not is_valid:
        error_msg = ". ".join(errors)
        if is_htmx(request):
            return HTMLResponse(
                content=f'<div class="alert alert-error">{error_msg}</div>',
                status_code=400,
            )
        flash(request, error_msg, "error")
        return RedirectResponse(url="/auth/profile", status_code=302)

    # Update password
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()

    if is_htmx(request):
        return HTMLResponse(
            content='<div class="alert alert-success">Password changed successfully</div>'
        )

    flash(request, "Password changed successfully", "success")
    return RedirectResponse(url="/auth/profile", status_code=302)


# API endpoints
@router.post("/api/login")
async def api_login(
    session: DBSession,
    credentials: UserLogin,
):
    """API login endpoint that returns user data."""
    # Check brute force protection
    if is_account_locked(credentials.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked",
        )
    
    user = authenticate_user(session, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return UserRead.model_validate(user)


@router.get("/api/me", response_model=UserRead)
async def get_current_user_api(user: CurrentUser):
    """Get current authenticated user."""
    return UserRead.model_validate(user)
