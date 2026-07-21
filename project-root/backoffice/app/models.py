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
from sqlalchemy import CheckConstraint, UniqueConstraint

db = SQLAlchemy()


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

    # One branch has many users (common users) and many stock lines.
    users = db.relationship("User", back_populates="branch")
    stock_items = db.relationship("Stock", back_populates="branch")

    def __repr__(self):
        return f"<Branch {self.name}>"


class User(db.Model):
    """
    A Backoffice account.

    - ADMIN: manages users only, never touches stock, has no branch.
    - COMMON_USER: manages stock for exactly one branch, never manages users.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)

    # Never store a plain-text password — this column holds a bcrypt hash
    # (see architecture.md, Decision 5).
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum(Role), nullable=False, default=Role.COMMON_USER)

    # Nullable on purpose: only common users need a branch. Admin has none.
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    branch = db.relationship("Branch", back_populates="users")

    # Soft-delete flag. A user is never hard-deleted from the database
    # (see architecture.md, section 4 — admin permissions).
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Encodes the role/branch business rule directly at the DB level,
        # not just in application code: an admin must have no branch, and
        # a common user must always have one.
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

    # Reference to the Product API only — not a local product record.
    product_id = db.Column(db.String(64), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=0)

    # Auto-updated whenever a common user adds or removes stock.
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    branch = db.relationship("Branch", back_populates="stock_items")

    __table_args__ = (
        # Quantity must never go negative — enforced at the DB level as a
        # safety net on top of the application-level check before any
        # add/remove operation (see architecture.md, section 5).
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
        # One row per (branch, product) pair: quantity is updated in place
        # rather than inserting a new row for every stock movement.
        UniqueConstraint("branch_id", "product_id", name="uq_branch_product"),
    )

    def __repr__(self):
        return f"<Stock branch={self.branch_id} product={self.product_id} qty={self.quantity}>"