"""SQLAlchemy base declarative class."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


from app.models.user import User  # noqa: E402, F401
from app.models.role import Permission, Role  # noqa: E402, F401
from app.models.translation import Language, Translation, TranslationProvider  # noqa: E402, F401
