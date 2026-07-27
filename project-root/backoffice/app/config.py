"""
HBntory — Flask configuration.

SSL/TLS is not required for this project (see architecture.md, section 4
of the SWE brief). Keep this simple and consistent across the team.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    # SQLite file lives at the project root of backoffice/, shared by
    # everyone on the team who runs the app locally.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'hbntory.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Used for Flask session signing (Souf's auth work depends on this).
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # External Product API (read-only, provided by the school — see
    # https://github.com/hbtn-edu/hbntory-products-api).
    PRODUCT_API_URL = os.environ.get("PRODUCT_API_URL", "http://127.0.0.1:5001")