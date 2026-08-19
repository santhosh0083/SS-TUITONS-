"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1 import (
    admin,
    ai,
    attendance,
    auth,
    health,
    messages,
    payments,
    people,
    scheduling,
)
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Refuse to boot production with development defaults.
    settings.assert_production_safe()
    yield
    await engine.dispose()


# The interactive docs enumerate every route, parameter and schema -- a map of
# the whole API, admin surface included. This one serves data about children,
# so it is not published. Off in production, on everywhere else.
_docs_enabled = not settings.is_production

app = FastAPI(
    title="SS Tuitions API",
    description="Backend for the SS Tuitions tutoring platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable) -> Response:
    """Add response headers that browsers act on.

    FORCE_HTTPS was required by assert_production_safe but read by nothing, so
    it asserted a guarantee the app never made. HSTS is what makes it real:
    once seen, the browser refuses to talk to this host over plain HTTP at
    all, closing the downgrade window from the first request onward.

    No HTTPS redirect is added here. The host terminates TLS and redirects at
    its edge already, and a second redirect driven by a misread
    X-Forwarded-Proto is how you get an infinite loop.
    """
    response: Response = await call_next(request)
    if settings.force_https:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(people.router, prefix="/api/v1/admin", tags=["people"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(scheduling.router, prefix="/api/v1", tags=["scheduling"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(
    attendance.router, prefix="/api/v1/attendance", tags=["attendance"]
)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running", "docs": "/docs"}
