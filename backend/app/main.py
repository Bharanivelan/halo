"""FastAPI application factory."""
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import accounts, auth, discovery, engagement, properties
from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import AppError, app_error_handler, unhandled_error_handler, validation_error_handler
from app.core.logging import configure_logging
from app.discovery import steps  # noqa: F401 — registers workflow steps

configure_logging()
settings = get_settings()
app = FastAPI(title="Halo API", version="0.2.0", openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_origin_regex=settings.cors_origin_regex,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Request-ID", "Content-Disposition"])


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
    request.state.request_id = rid
    response = await call_next(request)
    # Chrome Private/Local Network Access: lets an https Lovable preview call this API on localhost (D-37).
    if request.method == "OPTIONS" and request.headers.get("access-control-request-private-network") == "true" \
            and response.headers.get("access-control-allow-origin"):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

for r in (auth.router, properties.router, discovery.router, accounts.router, engagement.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    with engine.connect() as c:
        c.execute(text("select 1"))
    return {"ok": True, "llm_provider": settings.llm_provider, "llm_configured": settings.llm_configured, "search_configured": settings.search_configured}
