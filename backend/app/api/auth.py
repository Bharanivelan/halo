"""Auth endpoints: invite-only email + password, server-side sessions (P-01)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, text

from app.api.deps import CtxDep
from app.api.serializers import me_payload
from app.core.config import get_settings
from app.core.db import plain_session, tenant_session
from app.core.errors import RateLimited, Unauthenticated
from app.core.security import hash_password, hash_token, needs_rehash, new_token, verify_password
from app.models import AuditLog, LoginAttempt, Membership, SessionRow, User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


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
        token, csrf = new_token(), new_token()
        now = datetime.now(timezone.utc)
        db.add(SessionRow(token_hash=hash_token(token), user_id=user.id, workspace_id=m.workspace_id, membership_id=m.id,
                          csrf_token=csrf, idle_expires_at=now + timedelta(days=s.session_idle_days),
                          absolute_expires_at=now + timedelta(days=s.session_absolute_days), ip=ip,
                          user_agent=(request.headers.get("user-agent") or "")[:400]))
        user.last_login_at = now
        ws_id, uid = m.workspace_id, user.id
    with tenant_session(ws_id, uid) as tdb:
        tdb.add(AuditLog(workspace_id=ws_id, actor_user_id=uid, action="auth.login"))
    token_mode = s.token_auth_enabled and request.headers.get("X-Auth-Mode", "").lower() == "token"
    if not token_mode:
        response.set_cookie(s.session_cookie_name, token, httponly=True, secure=s.cookie_secure, samesite="lax",
                            path="/", max_age=s.session_absolute_days * 86400)
    with tenant_session(ws_id, uid) as tdb:
        payload = me_payload(tdb, user_id=uid, workspace_id=ws_id, membership_id=m.id, role=m.role, csrf=csrf)
    if token_mode:
        # Separate frontend (D-36): send as "Authorization: Bearer <access_token>". No CSRF header needed.
        payload["access_token"] = token
        payload["token_type"] = "bearer"
    return payload


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
