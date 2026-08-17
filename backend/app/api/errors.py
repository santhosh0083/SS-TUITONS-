"""Global exception handlers.

Two goals:

1. A database outage should look like a database outage — 503 with a clear
   message and a Retry-After header — not an opaque 500. Monitoring and load
   balancers treat those very differently.

2. Internal details never reach the client. Drivers put the connection string,
   including the password, into their exception messages. Those are logged
   server-side and replaced with a generic message in the response.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

DB_UNAVAILABLE_MESSAGE = (
    "The service is temporarily unable to reach its database. "
    "Please try again in a moment."
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OperationalError)
    async def _operational_error(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        # Connection refused, DNS failure, timeout, database asleep.
        logger.error(
            "Database unavailable handling %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DB_UNAVAILABLE_MESSAGE},
            headers={"Retry-After": "10"},
        )

    @app.exception_handler(DBAPIError)
    async def _dbapi_error(request: Request, exc: DBAPIError) -> JSONResponse:
        if exc.connection_invalidated:
            logger.error(
                "Database connection invalidated handling %s %s",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": DB_UNAVAILABLE_MESSAGE},
                headers={"Retry-After": "10"},
            )

        # A constraint violation, including our integrity triggers. The trigger
        # messages are written for humans, but they can name internal ids, so
        # they are logged rather than returned.
        logger.exception(
            "Database error handling %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "That request could not be completed."},
        )

    @app.exception_handler(OSError)
    async def _network_error(request: Request, exc: OSError) -> JSONResponse:
        """DNS failure, connection refused, or timeout reaching the database.

        These arrive as raw socket errors, not SQLAlchemy ones: asyncpg fails
        during address resolution, before SQLAlchemy has a DBAPI connection to
        wrap the error around. Without this handler a database outage surfaces
        as an opaque 500.
        """
        logger.error(
            "Network failure handling %s %s: %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DB_UNAVAILABLE_MESSAGE},
            headers={"Retry-After": "10"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_error(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception(
            "Unexpected database error handling %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )
