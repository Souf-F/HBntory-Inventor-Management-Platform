HBntory - Authentication and Authorization
1. Overview

The HBntory Backoffice uses session-based authentication (Flask-Login), with passwords hashed using bcrypt. There is no JWT token or API key: after logging in, the browser receives a signed session cookie, sent automatically with every subsequent request.

Authorization relies on two layers, both verified server-side: the account's role (Role) and, for common users, the branch that account is tied to (branch_id). No permission check is ever performed on the frontend: hiding a button in the interface is never treated as an access control.

2. Data model

Defined in backoffice/app/models.py.

python
class Role(enum.Enum):
    ADMIN = "admin"
    COMMON_USER = "common_user"

users table:

username — unique
password_hash — bcrypt, never stored in plain text
role — ADMIN or COMMON_USER
branch_id — foreign key to branches, nullable
is_active — boolean, used for soft-delete

A database-level constraint enforces role/branch consistency:

python
CheckConstraint(
    "(role = 'ADMIN' AND branch_id IS NULL) OR "
    "(role = 'COMMON_USER' AND branch_id IS NOT NULL)",
)

An admin never has a branch. A common user always has exactly one branch. This rule is enforced at schema creation time, not only at the application level.

User inherits from UserMixin (Flask-Login), which provides get_id(), is_authenticated, is_active, is_anonymous without redefining them manually.

3. Password hashing

In backoffice/routes/auth.py:

python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

The salt is generated automatically by bcrypt.gensalt() on every hash — two accounts sharing the same password never end up with the same stored hash.

4. Login (POST /login)
Look up the user by username
Reject if the user doesn't exist, if the password is incorrect, or if the account is disabled (is_active = False) — in all cases, the same generic message "Invalid credentials" is returned (401), so as not to reveal whether the username or the password was at fault
If everything checks out, login_user(user) creates the Flask-Login session
The response returns username, role, and branch_id — these three fields let the frontend know which view to route the user to (user list for an admin, stock view for a common user) without needing a second round-trip
5. Logout (POST /logout)

Protected by @login_required. Calls logout_user(), which invalidates the session server-side.

6. Role-based authorization: role_required

Defined in backoffice/routes/middleware.py:

python
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            if current_user.role not in roles:
                return jsonify({"status": "error", "message": "Access denied"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

Used as a decorator on every sensitive route, for example:

python
@role_required(Role.ADMIN)
def list_users(): ...

@role_required(Role.COMMON_USER)
def add_stock(branch_id): ...

Two distinct failure cases:

No valid session → 401 Unauthorized
Valid session but wrong role → 403 Access denied
7. Branch-based authorization: branch_required

Also in middleware.py, applied alongside role_required on stock routes:

python
def branch_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        branch_id = kwargs.get("branch_id")
        if current_user.branch_id != branch_id:
            return jsonify({"status": "error", "message": "Access denied"}), 403
        return f(*args, **kwargs)
    return wrapper

Compares the branch_id from the URL (/branches/<int:branch_id>/stock) against the connected account's own branch. A common user can never act on another branch's stock, even by manually editing the URL.

8. Permission matrix by route
Route	Method	Role required	Branch constraint
/login	POST	none	—
/logout	POST	authenticated	—
/users	GET, POST	ADMIN	—
/users/<id>	PATCH, DELETE	ADMIN	—
/users/<id>/reactivate	PATCH	ADMIN	—
/branches/<id>/stock	GET, POST	COMMON_USER	yes, own branch only
/branches/<id>/stock/remove	POST	COMMON_USER	yes, own branch only
/branches/<id>/stock/<product_id>	GET	COMMON_USER	yes, own branch only
/products	GET	COMMON_USER	—
/stock	GET	ADMIN	— (global multi-branch view, read-only)

An admin has no access to any stock-writing route. A common user has no access to any user-management route. This is not a frontend convention: every route explicitly refuses the call if the role doesn't match.

9. Account deletion: soft-delete only

DELETE /users/<id> never removes the row from the database. It sets is_active to False:

python
user.is_active = False
db.session.commit()

A disabled account can no longer log in (checked at login step 2), but its history (past stock operations, etc.) remains intact. PATCH /users/<id>/reactivate reverses the operation.

10. What authorization does not cover
No login attempt throttling (no rate limiting on /login) — out of scope for this project
No automatic session expiration beyond Flask-Login's default behavior
SECRET_KEY (used to sign session cookies) is hardcoded with a development value in app/config.py, to be overridden via the SECRET_KEY environment variable in a production setting
11. Boundary with the public site

The public site (client_web/) has no authentication and never calls Backoffice routes. It only queries the external product API (read-only) and the AI agent, which itself only has read access to stock (never write) through the MCP server's tools. No session data, no cookie, no role ever exists on the public site side.