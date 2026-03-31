"""Application entrypoint for the backend base service."""

import logging
from contextlib import asynccontextmanager

import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from app.core.config import settings
from app.core.exceptions import (
    general_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.db.session import engine
from app.router.endpoints import api_router
from app.core.logger import setup_logging
from app.core.email_limiter import error_email_limiter
from app.core.email import send_email

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage application startup and shutdown events."""
    setup_logging()
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))

        plain_startup_message = (
            f"Service '{settings.app_name}' v{settings.app_version} started successfully. "
            f"DB connection to '{settings.database_name}' on host '{settings.database_host}' is OK. "
            f"Pool size: {settings.database_pool_size}, Max overflow: {settings.database_max_overflow}. "
            f"Configured workers: {settings.workers}."
        )
        
        # Log startup messages
        # The plain message is sent to Tamarin, the rich one to console.
        green = "\033[92m"
        reset = "\033[0m"
        worker_info = f"Workers: {green}{settings.workers}{reset}"
        logger.info(f"🚀 Worker started for {settings.app_name} v{settings.app_version} | {worker_info}", extra={"plain_message": plain_startup_message})
        db_info = f"Host: {settings.database_host}, DB: {settings.database_name}, Pool: {settings.database_pool_size}/{settings.database_max_overflow}"
        logger.info(f"✅ Conexión a la base de datos exitosa: {db_info}")

    except Exception as e:
        error_message = f"Error al conectar con la base de datos: {e}"
        plain_error_message = (
            f"CRITICAL ERROR: Service startup failed. Could not connect to database "
            f"on host '{settings.database_host}'. Details: {e}"
        )
        # Log the plain message for Tamarin and email notifications
        logger.critical(plain_error_message)

        # Log a simple, colored message for the console
        red = "\033[91m"
        reset = "\033[0m"
        logger.error(f"❌ {red}ERROR CRÍTICO:{reset} No se pudo conectar a la base de datos en '{settings.database_host}'.")
        logger.error(f"   Detalle: {e}")
        if error_email_limiter.can_send():
            send_email(subject="Error de conexión a la base de datos", message=error_message)
        raise

    yield
    logger.info("🛑 Cerrando pools de conexiones y apagando el servicio...")
    await engine.dispose()  # SQLAlchemy engine handles the connection pool
    logger.info("🔌 Pools de conexiones cerrados. ¡Hasta luego!")


def create_application() -> FastAPI:
    """Build and configure the FastAPI application instance."""

    app_configs = {
        "title": settings.app_name,
        "version": settings.app_version,
        "lifespan": lifespan,
    }

    if not settings.swagger_enabled:
        app_configs["docs_url"] = None
        app_configs["redoc_url"] = None

    # If swagger user is set, protect the docs
    if settings.swagger_enabled and settings.user_swagger and settings.password_swagger:
        app_configs["docs_url"] = None
        app_configs["redoc_url"] = None

    application = FastAPI(**app_configs)

    # Add CORS middleware
    if settings.cors_enabled:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )

    # Register exception handlers
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    application.add_exception_handler(Exception, general_exception_handler)

    application.include_router(api_router)

    if settings.swagger_enabled and settings.user_swagger and settings.password_swagger:
        security = HTTPBasic()

        def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
            correct_username = secrets.compare_digest(credentials.username, settings.user_swagger)
            correct_password = secrets.compare_digest(credentials.password, settings.password_swagger)
            if not (correct_username and correct_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return credentials.username

        @application.get("/docs", include_in_schema=False)
        async def get_documentation(username: str = Depends(get_current_username)):
            return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

        @application.get("/redoc", include_in_schema=False)
        async def get_redoc_documentation(username: str = Depends(get_current_username)):
            return get_redoc_html(openapi_url="/openapi.json", title="redoc")

        @application.get("/openapi.json", include_in_schema=False)
        async def openapi(username: str = Depends(get_current_username)):
            return application.openapi()

    return application


app = create_application()
