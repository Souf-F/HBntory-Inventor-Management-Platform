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

# Stock is deliberately NOT a copy of the catalog. The external Product API
# lists 39 products; a branch only holds what it actually stocks. The layout
# below is built so the AI assistant has meaningful cases to answer:
#
#   - products stocked in all three branches, at different quantities
#     -> "where can I find X?" returns several branches
#   - products exclusive to one branch
#     -> "where can I find X?" returns exactly one
#   - Paris alone can satisfy a full shopping list, the others cannot
#     -> "I need 3 of X, 2 of Y, 4 of Z, which branch?" has one answer
#   - several catalog products are stocked nowhere
#     -> "where can I find X?" must answer "nowhere", not invent a branch
#
# The golden rule still applies: only the identifier is stored here, never
# a name, a price or any other product detail.

STOCK_BY_BRANCH = {
    # --- Branch 1: HBntory Paris — the largest, can fulfil a full order ---
    "HBntory Paris": {
        "HB-LAP-1001": 24,   # also in Lyon and Marseille
        "HB-LAP-1002": 12,   # also in Lyon
        "HB-MON-2101": 18,   # also in Lyon and Marseille
        "HB-MON-2102": 40,   # also in Marseille
        "HB-DCK-3001": 15,
        "HB-KBD-4101": 30,   # also in Lyon and Marseille
        "HB-MSE-4201": 45,   # also in Lyon
        "HB-CAM-5101": 9,
        "HB-SSD-7101": 22,   # also in Marseille
        "HB-PWR-8101": 33,
        "HB-BAG-1011": 17,   # Paris only
        "HB-PRN-1501": 4,    # Paris only
    },
    # --- Branch 2: HBntory Lyon — mid-sized, misses some items ---
    "HBntory Lyon": {
        "HB-LAP-1001": 8,
        "HB-LAP-1002": 3,
        "HB-MON-2101": 11,
        "HB-KBD-4101": 16,
        "HB-KBD-4102": 20,   # Lyon only
        "HB-MSE-4201": 27,
        "HB-MIC-5201": 6,    # also in Marseille
        "HB-USB-7201": 50,
        "HB-SEC-1401": 12,   # Lyon only
    },
    # --- Branch 3: HBntory Marseille — smallest, a few exclusives ---
    "HBntory Marseille": {
        "HB-LAP-1001": 5,
        "HB-MON-2101": 7,
        "HB-MON-2102": 14,
        "HB-KBD-4101": 9,
        "HB-MIC-5201": 3,
        "HB-SSD-7101": 6,
        "HB-TAB-1701": 8,    # Marseille only
    },
}


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
            Branch(name="HBntory Paris", location="Paris"),
            Branch(name="HBntory Lyon", location="Lyon"),
            Branch(name="HBntory Marseille", location="Marseille"),
        ]
        db.session.add_all(branches)
        db.session.flush()  # assign ids before using them below

        branch_by_name = {branch.name: branch for branch in branches}

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

        # --- Stock, laid out per branch (see STOCK_BY_BRANCH above) ---
        stock_rows = 0
        for branch_name, products in STOCK_BY_BRANCH.items():
            branch = branch_by_name[branch_name]
            for product_id, quantity in products.items():
                db.session.add(
                    Stock(branch_id=branch.id, product_id=product_id, quantity=quantity)
                )
                stock_rows += 1

        db.session.commit()
        print(
            f"Database seeded: {len(branches)} branches, 1 admin, "
            f"{len(branches)} common users, {stock_rows} stock rows."
        )


if __name__ == "__main__":
    seed()
    