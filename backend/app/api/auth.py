"""Auth endpoints: email + password sign-in and self-service sign-up (D-51), server-side sessions (P-01)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text

from app.api.deps import CtxDep
from app.api.serializers import me_payload
from app.core.config import get_settings
from app.core.db import plain_session, tenant_session
from app.core.errors import Conflict, Forbidden, RateLimited, Unauthenticated, ValidationFailed
from app.core.security import hash_password, hash_token, needs_rehash, new_token, verify_password
from app.models import AuditLog, LoginAttempt, Membership, SessionRow, User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class SignupIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(max_length=200)
    company: str | None = Field(default=None, max_length=200)


def _start_session(*, request: Request, response: Response, user_id: UUID, workspace_id: UUID, membership_id: UUID,
                   role: str, action: str) -> dict:
    """Create a server-side session and answer like /auth/me (+ access_token in token mode, D-36)."""
    s = get_settings()
    ip = request.client.host if request.client else "unknown"
    token, csrf = new_token(), new_token()
    now = datetime.now(timezone.utc)
    with plain_session() as db:
        db.add(SessionRow(token_hash=hash_token(token), user_id=user_id, workspace_id=workspace_id, membership_id=membership_id,
                          csrf_token=csrf, idle_expires_at=now + timedelta(days=s.session_idle_days),
                          absolute_expires_at=now + timedelta(days=s.session_absolute_days), ip=ip,
                          user_agent=(request.headers.get("user-agent") or "")[:400]))
        db.execute(text("UPDATE users SET last_login_at = :t WHERE id = :u"), {"t": now, "u": user_id})
    with tenant_session(workspace_id, user_id) as tdb:
        tdb.add(AuditLog(workspace_id=workspace_id, actor_user_id=user_id, action=action))
    token_mode = s.token_auth_enabled and request.headers.get("X-Auth-Mode", "").lower() == "token"
    if not token_mode:
        response.set_cookie(s.session_cookie_name, token, httponly=True, secure=s.cookie_secure, samesite="lax",
                            path="/", max_age=s.session_absolute_days * 86400)
    with tenant_session(workspace_id, user_id) as tdb:
        payload = me_payload(tdb, user_id=user_id, workspace_id=workspace_id, membership_id=membership_id, role=role, csrf=csrf)
    if token_mode:
        # Separate frontend (D-36): send as "Authorization: Bearer <access_token>". No CSRF header needed.
        payload["access_token"] = token
        payload["token_type"] = "bearer"
    return payload


@router.get("/options")
def auth_options():
    """Public: which ways to sign in this server offers (the sign-in page reads this)."""
    s = get_settings()
    return {"signup_enabled": s.signup_enabled, "password_min_length": s.password_min_length,
            "google_enabled": False}  # Google sign-in: planned (D-51)


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response):
    """Create an account with its own workspace; the new user is its admin and is signed in."""
    from app.core.accounts import EmailTaken, create_workspace_with_admin

    s = get_settings()
    if not s.signup_enabled:
        raise Forbidden("Sign-up is turned off on this server. Ask your Halo admin for an account.")
    ip = request.client.host if request.client else "unknown"
    key = f"signup|{ip}"
    with plain_session() as db:
        recent = db.execute(select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.key == key, LoginAttempt.created_at > datetime.now(timezone.utc) - timedelta(hours=1))).scalar_one()
        if recent >= s.signup_rate_limit_per_hour:
            raise RateLimited("Too many accounts created from this network. Try again in an hour.")
        db.add(LoginAttempt(key=key, success=True))
    name = body.full_name.strip()
    if not name:
        raise ValidationFailed("Enter your name.")
    if len(body.password) < s.password_min_length:
        raise ValidationFailed(f"Use a password of at least {s.password_min_length} characters.")
    if body.password.strip().lower() == str(body.email).lower():
        raise ValidationFailed("Don't use your email address as your password.")
    company = (body.company or "").strip()
    ws_name = company or f"{name.split()[0]}'s workspace"
    try:
        acct = create_workspace_with_admin(workspace_name=ws_name, email=str(body.email), full_name=name, password=body.password,
                                           unique_slug=True)
    except EmailTaken:
        raise Conflict("An account with this email already exists. Sign in instead.") from None
    return _start_session(request=request, response=response, user_id=acct.user_id, workspace_id=acct.workspace_id,
                          membership_id=acct.membership_id, role="admin", action="auth.signup")


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    s = get_settings()
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}|{body.email.lower()}"
    with plain_session() as db:
        recent = db.execute(select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.key == key, LoginAttempt.success.is_(False),
            LoginAttempt.created_at > datetime.now(timezone.utc) - timedelta(minutes=1))).scalar_one()
        if recent >= s.login_rate_limit_per_min:
            raise RateLimited("Too many sign-in attempts. Wait a minute and try again.")
        user = db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none()
        ok = bool(user and user.is_active and verify_password(user.password_hash, body.password))
        db.add(LoginAttempt(key=key, success=ok))
        if not ok:
            db.commit()
            raise Unauthenticated("Email or password is incorrect.")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(body.password)
        m = db.execute(select(Membership).where(Membership.user_id == user.id, Membership.is_active.is_(True))
                       .order_by(Membership.created_at)).scalars().first()
        if m is None:
            raise Unauthenticated("Your account isn't a member of any workspace.")
        ws_id, uid, mid, role = m.workspace_id, user.id, m.id, m.role
    return _start_session(request=request, response=response, user_id=uid, workspace_id=ws_id, membership_id=mid,
                          role=role, action="auth.login")


@router.post("/logout", status_code=204)
def logout(ctx: CtxDep, response: Response):
    ctx.db.execute(text("UPDATE sessions SET revoked_at = now() WHERE id = :id"), {"id": ctx.p.session_id})
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return Response(status_code=204)


@router.get("/me")
def me(ctx: CtxDep):
    p = ctx.p
    return me_payload(ctx.db, user_id=p.user_id, workspace_id=p.workspace_id, membership_id=p.membership_id,
                      role=p.role, csrf=p.csrf_token)
