"""
Read-only access to the shared database (branches, stock), owned by the
Backoffice.

Imports Branch/Stock directly from backoffice/app/models.py instead of
redefining the schema here, so a column change on the Backoffice side is
automatically reflected in the MCP server too (see architecture.md,
Decision 2). This uses a plain SQLAlchemy session bound to its own engine,
not Flask-SQLAlchemy's db.session, since this process never runs inside a
Flask app context.
"""

import os
import sys

_BACKOFFICE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backoffice"
)
if _BACKOFFICE_DIR not in sys.path:
    sys.path.insert(0, _BACKOFFICE_DIR)

from app.models import Branch, Stock  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(_BACKOFFICE_DIR, 'hbntory.db')}"
)

_engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=_engine)

__all__ = ["Branch", "Stock", "Session"]
