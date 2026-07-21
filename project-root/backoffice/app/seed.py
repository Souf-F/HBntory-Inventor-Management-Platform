"""
HBntory — Database seed script.

Creates the SQLite file (via db.create_all()) and populates it with:
- a few branches
- the one admin account
- a couple of common users (one per branch, for testing)
- test stock rows, using product_id values matching the team's test
  product list (see recap_complet_hbntory.md, section 9)

Run with:
    python seed.py

Safe to re-run: skips seeding if data already exists.
"""

import bcrypt

from app import create_app
from app.models import db, Branch, User, Role, Stock

app = create_app()

# Product IDs used for local testing only — actual product details always
# come from the external Product API, never stored here (golden rule).
TEST_PRODUCT_IDS = [
    "prod-001",  # Huile de tournesol 5L
    "prod-002",  # Farine T55 25kg
    "prod-003",  # Sucre en poudre 5kg
    "prod-004",  # Café en grains 1kg
    "prod-005",  # Tomates pelées 2,5kg
    "prod-006",  # Essuie-tout pro (carton de 6)
    "prod-007",  # Gants latex jetables (boîte de 100)
    "prod-008",  # Riz basmati 5kg
    "prod-009",  # Eau plate 1,5L (pack de 6)
    "prod-010",  # Produit d'entretien sol multi-usage 5L
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

        # --- Test stock: spread the 10 test products across branches ---
        for i, product_id in enumerate(TEST_PRODUCT_IDS):
            branch = branches[i % len(branches)]
            db.session.add(
                Stock(branch_id=branch.id, product_id=product_id, quantity=(i + 1) * 10)
            )

        db.session.commit()
        print("Database seeded: 3 branches, 1 admin, 3 common users, 10 stock rows.")


if __name__ == "__main__":
    seed()