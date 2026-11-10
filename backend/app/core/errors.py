"""Typed application errors mapped to RFC 9457 problem+json responses."""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_BASE = "https://inhabitr.app/problems/"


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
    return _problem(request, 500, "internal-error", "Something went wrong", "The error has been logged.")
