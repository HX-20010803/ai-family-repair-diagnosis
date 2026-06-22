from __future__ import annotations

from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine


Base.metadata.create_all(bind=engine)
print("database schema is ready")
