"""
HBntory — SQLAlchemy models

Shared database schema between the Backoffice and the AI Service
(see architecture.md, section 6 — Decision 3).

Golden rules enforced here:
- No product data (name, description, price, image) is ever stored locally.
  Only the external product_id is kept, as a reference into the Product API.
- Stock quantity is never allowed to go negative (DB-level CHECK constraint,
  on top of application-level validation).
- A common user is always tied to exactly one branch; an admin is not tied
  to any branch, since the admin never manages stock.
"""

from datetime import datetime
import enum

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint, event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


# SQLite does not enforce FOREIGN KEY constraints by default, even though
# they are declared below (branch_id -> branches.id). Without this, a row
# could reference a branch_id that doesn't exist in the branches table,
# silently, with no error. This listener turns the check on for every new
# SQLite connection opened by SQLAlchemy.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Role(enum.Enum):
    """Backoffice roles. There is only ever one ADMIN account (see architecture.md)."""
    ADMIN = "admin"
    COMMON_USER = "common_user"


class Branch(db.Model):
    """A physical branch of the company. Holds its own stock independently."""

    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", back_populates="branch")
    stock_items = db.relationship("Stock", back_populates="branch")

    def __repr__(self):
        return f"<Branch {self.name}>"


class User(UserMixin, db.Model):
    """
    A Backoffice account.

    - ADMIN: manages users only, never touches stock, has no branch.
    - COMMON_USER: manages stock for exactly one branch, never manages users.

    Inherits from UserMixin to satisfy Flask-Login's required interface
    (get_id, is_authenticated, is_active, is_anonymous) without redefining
    them by hand.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum(Role), nullable=False, default=Role.COMMON_USER)

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    branch = db.relationship("Branch", back_populates="users")

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(role = 'ADMIN' AND branch_id IS NULL) OR "
            "(role = 'COMMON_USER' AND branch_id IS NOT NULL)",
            name="ck_admin_no_branch_common_user_has_branch",
        ),
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"


class Stock(db.Model):
    """
    Stock quantity of one product in one branch.

    Deliberately minimal: only product_id is stored, never product details
    (name, description, price, image) — those always come from the external
    Product API, called on demand (see architecture.md, section 3).
    """

    __tablename__ = "stock"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)

    product_id = db.Column(db.String(64), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=0)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    branch = db.relationship("Branch", back_populates="stock_items")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
        UniqueConstraint("branch_id", "product_id", name="uq_branch_product"),
    )

    def __repr__(self):
        return f"<Stock branch={self.branch_id} product={self.product_id} qty={self.quantity}>"
