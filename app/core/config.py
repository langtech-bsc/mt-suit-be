from __future__ import annotations

from functools import cached_property, lru_cache
from pydantic import AliasChoices, BaseModel, Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


# ----------------------------- Submodels ------------------------------ #

class DatabaseSettings(BaseModel):
    """Derived database configuration (sync/async)."""
    url: str
    async_url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


# --------------------------- Main Settings ---------------------------- #

class Settings(BaseSettings):
    """
    Global app settings loaded from environment.
    - Loads .env (UTF-8)
    - Ignores extra keys
    - case_sensitive=False to be friendlier in tests and local envs
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "Backend Base"
    app_version: str = "0.1.0"
    workers: int = Field(2, validation_alias=AliasChoices("WORKERS", "workers"))

    swagger_enabled: bool = Field(default=True, alias="SWAGGER_ENABLED")
    user_swagger: str | None = Field(default=None, alias="USER_SWAGGER")
    password_swagger: str | None = Field(default=None, alias="PASSWORD_SWAGGER")

    # ---- CORS ----
    cors_enabled: bool = Field(default=True, validation_alias=AliasChoices("CORS_ENABLED", "cors_enabled"))
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias=AliasChoices("CORS_ALLOW_CREDENTIALS", "cors_allow_credentials"))
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias=AliasChoices("CORS_ALLOW_METHODS", "cors_allow_methods"),
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias=AliasChoices("CORS_ALLOW_HEADERS", "cors_allow_headers"),
    )

    # ---- JWT & Security ----
    jwt_secret_key: SecretStr = Field(
        SecretStr("your-secret-key-change-this-in-production"),
        validation_alias=AliasChoices("JWT_SECRET_KEY", "jwt_secret_key"),
    )
    jwt_algorithm: str = Field("HS256", validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"))
    jwt_access_token_expire_minutes: int = Field(
        30,
        validation_alias=AliasChoices("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "jwt_access_token_expire_minutes"),
    )

    # Encryption key for sensitive data (API keys, etc.)
    encryption_key: SecretStr = Field(
        SecretStr("D4xdS3PwWl5jxNmhpyKMBuBSgqbxEmO_wfLRZWLSR5o="),
        validation_alias=AliasChoices("ENCRYPTION_KEY", "encryption_key"),
    )

    # ---- DB (base values) ----
    database_url: str | None = Field(default=None, validation_alias=AliasChoices("DATABASE_URL", "database_url"))
    database_host: str = Field("localhost", validation_alias=AliasChoices("DB_HOST", "database_host"))
    database_port: int = Field(5432, validation_alias=AliasChoices("DB_PORT", "database_port"))
    database_user: str = Field("postgres", validation_alias=AliasChoices("DB_USER", "database_user"))
    database_password: SecretStr = Field(
        SecretStr("postgres"),
        validation_alias=AliasChoices("DB_PASSWORD", "database_password"),
    )
    database_name: str = Field("backend_app", validation_alias=AliasChoices("DB_NAME", "database_name"))
    database_echo: bool = Field(False, validation_alias=AliasChoices("DB_ECHO", "database_echo"))
    database_pool_size: int = Field(5, validation_alias=AliasChoices("DB_POOL_SIZE", "database_pool_size"))
    database_max_overflow: int = Field(10, validation_alias=AliasChoices("DB_MAX_OVERFLOW", "database_max_overflow"))

    # ---- Logging ----
    log_level: str = Field("DEBUG", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))
    log_to_file: bool = Field(True, validation_alias=AliasChoices("LOG_TO_FILE", "log_to_file"))
    log_json: bool = Field(False, validation_alias=AliasChoices("LOG_JSON", "log_json"))
    log_color: bool = Field(True, validation_alias=AliasChoices("LOG_COLOR", "log_color"))
    log_dir: str = Field("logs", validation_alias=AliasChoices("LOG_DIR", "log_dir"))
    log_filename: str = Field("app.log", validation_alias=AliasChoices("LOG_FILENAME", "log_filename"))

    # ---- Tamarin ----
    tamarin_logs_enabled: bool = Field(False, validation_alias=AliasChoices("TAMARIN_LOGS_ENABLED", "tamarin_logs_enabled"))
    tamarin_app_name: str = Field("Backend Base", validation_alias=AliasChoices("TAMARIN_APP_NAME", "tamarin_app_name"))
    tamarin_app_token: SecretStr | None = Field(default=None, validation_alias=AliasChoices("TAMARIN_APP_TOKEN", "tamarin_app_token"))
    tamarin_api_url: str = Field(
        "https://tamarin.macaqueconsulting.com/v1/tamarin/logs",
        validation_alias=AliasChoices("TAMARIN_API_URL", "tamarin_api_url"),
    )

    # ---- Mailjet ----
    mailjet_enabled: bool = Field(False, validation_alias=AliasChoices("MAILJET_ENABLED", "mailjet_enabled"))
    mailjet_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("MAILJET_API_KEY", "mailjet_api_key"))
    mailjet_api_secret: SecretStr | None = Field(default=None, validation_alias=AliasChoices("MAILJET_API_SECRET", "mailjet_api_secret"))
    mailjet_sender_email: str | None = Field(default=None, validation_alias=AliasChoices("MAILJET_SENDER_EMAIL", "mailjet_sender_email"))
    mailjet_sender_name: str | None = Field(default=None, validation_alias=AliasChoices("MAILJET_SENDER_NAME", "mailjet_sender_name"))
    # Accepts JSON list or CSV in .env
    mailjet_receiver_emails: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MAILJET_RECEIVER_EMAILS", "mailjet_receiver_emails"),
    )

    # --------------------- Normalization / Validation ------------------- #

    @model_validator(mode="after")
    def _normalize_and_assemble(self) -> "Settings":
        # 1) Build DATABASE_URL if not provided
        if not self.database_url:
            self.database_url = self._build_sync_url()

        # 2) Validate supported driver (PostgreSQL only)
        try:
            url = make_url(self.database_url)
        except Exception as ex:  # noqa: BLE001
            raise ValidationError.from_exception_data(
                title="Invalid DATABASE_URL",
                line_errors=[],
            ) from ex

        if not url.drivername.startswith("postgresql"):
            raise ValueError(
                "Unsupported driver: PostgreSQL only (postgresql / postgresql+psycopg / postgresql+asyncpg)."
            )

        # 3) Coerce emails from CSV if they arrived as a string
        if isinstance(self.mailjet_receiver_emails, str):
            self.mailjet_receiver_emails = [
                e.strip() for e in self.mailjet_receiver_emails.split(",") if e.strip()
            ]

        # 4) Coerce CORS origins/methods/headers from CSV if they arrived as a string
        if isinstance(self.cors_origins, str):
            self.cors_origins = [
                o.strip() for o in self.cors_origins.split(",") if o.strip()
            ]
        if isinstance(self.cors_allow_methods, str):
            self.cors_allow_methods = [
                m.strip() for m in self.cors_allow_methods.split(",") if m.strip()
            ]
        if isinstance(self.cors_allow_headers, str):
            self.cors_allow_headers = [
                h.strip() for h in self.cors_allow_headers.split(",") if h.strip()
            ]

        return self

    # ----------------------------- DB helpers --------------------------- #

    def _build_sync_url(self) -> str:
        """
        Generate an explicit sync DSN using the modern psycopg3 driver.
        Avoids leaking secrets: unwrap SecretStr only here.
        """
        return URL.create(
            "postgresql+psycopg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    @cached_property
    def database(self) -> DatabaseSettings:
        """
        Cached (per-process) derived DB settings.
        - Force sync driver to psycopg3
        - Derive async DSN using asyncpg
        """
        sync = make_url(self.database_url).set(drivername="postgresql+psycopg")
        async_ = sync.set(drivername="postgresql+asyncpg")
        return DatabaseSettings(
            url=sync.render_as_string(hide_password=False),
            async_url=async_.render_as_string(hide_password=False),
            echo=self.database_echo,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
        )


# ---------------------------- Access point ----------------------------- #

@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read-only usage)."""
    return Settings()


# Typical usage
settings = get_settings()
