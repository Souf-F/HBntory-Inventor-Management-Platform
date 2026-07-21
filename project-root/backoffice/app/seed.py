"""
HBntory — Database seed script.

Creates the SQLite file (via db.create_all()) and populates it with:
- a few branches
- the one admin account
- a couple of common users (one per branch, for testing)
- test stock rows, using product_id (SKU) values matching real entries
  from the Product API test catalog (e.g. "HB-LAP-1001")

This file lives inside the app/ package, so it must be run as a module
from the backoffice/ root directory:

    python3 -m app.seed

Running it as a plain script (python3 seed.py) will fail with an import
error, since relative imports only work when Python recognizes app/ as
a package (which -m does, but a direct script call does not).

Safe to re-run: skips seeding if data already exists.
"""

import bcrypt

from . import create_app
from .models import db, Branch, User, Role, Stock

app = create_app()

# SKUs used for local testing. Match these against real entries in the
# Product API test catalog where possible (see product_api.py) — the
# golden rule still applies: no product details are stored here, only
# the identifier.
TEST_PRODUCT_IDS = [
    "HB-LAP-1001",
    "HB-LAP-1002",
    "HB-MON-2101",
    "HB-MON-2102",
    "HB-DCK-3001",
    "HB-KBD-4101",
    "HB-KBD-4102",
    "HB-MSE-4201",
    "HB-CAM-5101",
    "HB-MIC-5201",
]


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed():
    with app.app_context():
        db.create_all()

        if User.query.first():
            print("Database already seeded — skipping.")
            return

        # --- Branches ---
        branches = [
            Branch(name="Metro Paris Nord", location="Paris"),
            Branch(name="Metro Lyon Part-Dieu", location="Lyon"),
            Branch(name="Metro Marseille Sud", location="Marseille"),
        ]
        db.session.add_all(branches)
        db.session.flush()  # assign ids before using them below

        # --- Admin (single account, no branch) ---
        admin = User(
            username="admin",
            password_hash=hash_password("ChangeMe123!"),
            role=Role.ADMIN,
            branch_id=None,
            is_active=True,
        )
        db.session.add(admin)

        # --- One common user per branch, for testing ---
        for i, branch in enumerate(branches, start=1):
            user = User(
                username=f"employee{i}",
                password_hash=hash_password("ChangeMe123!"),
                role=Role.COMMON_USER,
                branch_id=branch.id,
                is_active=True,
            )
            db.session.add(user)

        # --- Test stock: spread the test SKUs across branches ---
        for i, product_id in enumerate(TEST_PRODUCT_IDS):
            branch = branches[i % len(branches)]
            db.session.add(
                Stock(branch_id=branch.id, product_id=product_id, quantity=(i + 1) * 10)
            )

        db.session.commit()
        print("Database seeded: 3 branches, 1 admin, 3 common users, 10 stock rows.")


if __name__ == "__main__":
    seed()