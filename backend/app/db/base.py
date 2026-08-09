from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Alembic will inspect this metadata to generate database migrations.
    """

    pass