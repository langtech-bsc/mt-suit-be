"""Global exception handlers for the FastAPI application."""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: The incoming request
        exc: The validation exception

    Returns:
        JSON response with validation error details
    """
    errors = []
    for error in exc.errors():
        error_detail = {
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        }
        errors.append(error_detail)

    logger.warning(f"Validation error on {request.url.path}: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Validation error",
        },
    )


def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.

    Args:
        request: The incoming request
        exc: The SQLAlchemy exception

    Returns:
        JSON response with error details
    """
    logger.error(f"Database error on {request.url.path}: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "message": "An error occurred while processing your request",
        },
    )


def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSON response with error details
    """
    logger.error(
        f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": f"Internal server error: {type(exc).__name__}",
        },
    )
