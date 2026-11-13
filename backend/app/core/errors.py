"""Typed application errors mapped to RFC 9457 problem+json responses."""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_BASE = "https://halo.app/problems/"


class AppError(Exception):
    status = 400
    slug = "bad-request"
    title = "Bad request"

    def __init__(self, detail: str | None = None, *, errors: list[dict] | None = None):
        super().__init__(detail or self.title)
        self.detail = detail
        self.errors = errors


class NotFound(AppError):
    status, slug, title = 404, "not-found", "Not found"


class Unauthenticated(AppError):
    status, slug, title = 401, "unauthenticated", "Sign in required"


class Forbidden(AppError):
    status, slug, title = 403, "forbidden", "Not allowed"


class Conflict(AppError):
    status, slug, title = 409, "conflict", "Conflict"


class ValidationFailed(AppError):
    status, slug, title = 422, "validation-error", "Validation failed"


class RateLimited(AppError):
    status, slug, title = 429, "rate-limited", "Too many requests"


class FeatureUnavailable(AppError):
    status, slug, title = 409, "feature-unavailable", "Feature not configured"


def _problem(request: Request, status: int, slug: str, title: str, detail: str | None, errors=None):
    body = {
        "type": PROBLEM_BASE + slug,
        "title": title,
        "status": status,
        "instance": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
    }
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def app_error_handler(request: Request, exc: AppError):
    return _problem(request, exc.status, exc.slug, exc.title, exc.detail, exc.errors)


async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query", "path")),
            "code": e.get("type", "invalid"),
            "message": e.get("msg", "Invalid value"),
        }
        for e in exc.errors()
    ]
    return _problem(request, 422, "validation-error", "Validation failed", errors[0]["message"] if errors else None, errors)


async def unhandled_error_handler(request: Request, exc: Exception):
    import structlog

    structlog.get_logger().exception("unhandled_error", path=request.url.path)
    return with_cors(request, _problem(request, 500, "internal-error", "Something went wrong",
                                       "Something went wrong on the server. Please try again."))


def _friendly(msg: str) -> str:
    if msg.startswith("AI provider temporarily unavailable"):
        return "The AI is busy right now. Wait a minute and try again."
    if msg.startswith("Geocoder is busy"):
        return "Address search is busy right now. Wait a few seconds and try again."
    return msg


async def transient_error_handler(request: Request, exc: Exception):
    """Busy upstream (AI, geocoder, news) → 503 with a plain message the UI can show (instead of a 500 the browser hides)."""
    return _problem(request, 503, "service-busy", "Service busy", _friendly(str(exc)))


async def permanent_error_handler(request: Request, exc: Exception):
    """Upstream refused (e.g. AI daily allowance used up, bad key) → 503; messages are written for users."""
    from app.workflow.errors import AIQuotaExhausted

    detail = ("The AI's daily allowance is used up. Try again tomorrow, or add a paid AI key on the server."
              if isinstance(exc, AIQuotaExhausted) else str(exc))
    return _problem(request, 503, "service-unavailable", "Service unavailable", detail)


def with_cors(request: Request, response: JSONResponse) -> JSONResponse:
    """Unhandled 500s are rendered outside the CORS middleware; add the header so browsers can read the error."""
    import re

    from app.core.config import get_settings

    origin = request.headers.get("origin")
    s = get_settings()
    if origin and (origin in s.cors_origins or (s.cors_origin_regex and re.fullmatch(s.cors_origin_regex, origin))):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response
