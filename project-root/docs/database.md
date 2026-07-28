# Database Design — HBntory Backoffice

Documentation for Task 1: relational schema, SQLAlchemy models, initial data and
validation rules.

Implementation: `backoffice/app/models.py` · Seed script: `backoffice/app/seed.py`

---

## 1. Design principles

Two constraints shaped every decision below.

**No product data is stored locally.** Product names, descriptions, prices, images and
metadata belong to the external Product API. Our database stores only the product
identifier (SKU) needed to attach a stock quantity to a catalog entry. There is no
`products` table — not as an oversight, but by design: with nowhere to put a product name,
the rule cannot be broken by accident.

**No table exists unless a requirement needs it.** We considered a `stock_movements`
history table and a `suppliers` table. Both are realistic for an inventory system, and
both were left out: the mandatory scope requires current stock levels, not an audit trail,
and supplier data already lives in the Product API.

---

## 2. Schema

### `branches`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String(100) | Not null, unique |
| `location` | String(255) | Nullable |
| `created_at` | DateTime | Defaults to creation time |

A physical branch of the company. Each branch holds its own stock independently.

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key |
| `username` | String(80) | Not null, unique |
| `password_hash` | String(255) | Not null |
| `role` | Enum(`ADMIN`, `COMMON_USER`) | Not null, defaults to `COMMON_USER` |
| `branch_id` | Integer | Foreign key → `branches.id`, nullable |
| `is_active` | Boolean | Not null, defaults to `True` |
| `created_at` | DateTime | Defaults to creation time |

`branch_id` is nullable at the column level because the admin has no branch, but the
combination is constrained at the table level:

```sql
CHECK (
  (role = 'ADMIN'        AND branch_id IS NULL) OR
  (role = 'COMMON_USER'  AND branch_id IS NOT NULL)
)
```

This enforces two project rules at once: a common user belongs to exactly one branch, and
the admin — who never manages stock — is not attached to any.

`is_active` implements soft deletion. A deactivated user keeps their row, their history and
their identifier; only their ability to authenticate is revoked.

### `stock`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | Primary key |
| `branch_id` | Integer | Foreign key → `branches.id`, not null |
| `product_id` | String(64) | Not null — external SKU |
| `quantity` | Integer | Not null, defaults to 0 |
| `updated_at` | DateTime | Refreshed on every update |

Two table-level constraints:

```sql
CHECK (quantity >= 0)                    -- ck_stock_quantity_non_negative
UNIQUE (branch_id, product_id)           -- uq_branch_product
```

The `UNIQUE` pair means a given product has at most one stock row per branch, so adding
stock updates an existing row rather than creating a duplicate one.

`product_id` is a plain string with no relationship to any local table. It holds a SKU such
as `HB-MON-2102`, which is the identifier the Product API itself uses in its detail
endpoint (`/api/v1/products/HB-MON-2102`).

### Relationships

```
branches 1 ──── * users      (a branch has many users; a common user has one branch)
branches 1 ──── * stock      (a branch has many stock rows)
stock    * ──── ? products   (by SKU only — resolved through the external API)
```

The third relationship is deliberately not a foreign key. It cannot be: the other side of
it lives in a different system.

---

## 3. SQLAlchemy notes

### Foreign key enforcement on SQLite

SQLite does not enforce `FOREIGN KEY` constraints by default, even when they are declared.
Without intervention, a stock row could reference a branch that does not exist — silently,
with no error raised. `models.py` registers a SQLAlchemy engine listener that runs
`PRAGMA foreign_keys=ON` on every new connection.

Side effect worth knowing: once foreign keys are enforced, an invalid `branch_id` raises an
`IntegrityError` rather than passing through. The routes therefore validate `branch_id`
before insertion, so the caller receives a clear 400 instead of a 500.

### Enum storage

`db.Enum(Role)` stores the *member name* (`ADMIN`, `COMMON_USER`), not the value
(`admin`, `common_user`). The `CHECK` constraint above compares against the stored names
accordingly.

### `is_active` and Flask-Login

`User` inherits from `UserMixin`, which provides an `is_active` property. Our column of the
same name overrides it, intentionally: Flask-Login then reads the real database value, so
a soft-deleted account is rejected wherever the framework consults `is_active`.

---

## 4. Initial data

`backoffice/app/seed.py`, run as a module from the `backoffice/` directory:

```bash
python3 -m app.seed
```

It creates the tables via `db.create_all()` and populates:

- 3 branches (Paris, Lyon, Marseille)
- 1 admin account, with no branch
- 3 common users, one per branch
- 10 stock rows spread across the branches, using SKUs from the Product API test catalog

Passwords are hashed with bcrypt before insertion, no plain-text password is ever written
to the database, including the admin's.

The script is idempotent: it checks for an existing user and exits early if the database
has already been seeded, so re-running it is safe.

**Known limitation.** `db.create_all()` only creates missing tables; it never alters
existing ones. A database file created before a constraint was added will not gain that
constraint. During development, the fix is to delete the file and re-seed. A production
system would use Alembic migrations instead.

---

## 5. Validation rules

Validation is deliberately placed at **two levels**, because the two serve different purposes.

### Application level — routes

| Rule | Where | Response |
|---|---|---|
| Quantity must be a positive integer | `add_stock`, `remove_stock` | 400 |
| Cannot remove more than available | `remove_stock` | 400 |
| Branch must exist | `create_user`, `update_user` | 400 |
| Product must exist in the external catalog | `add_stock` | 404 |
| Catalog unreachable on a write | `add_stock` | 503 |

The application layer exists to produce **clear, actionable errors**. "Not enough stock
available" is useful to an employee; a raw SQL exception is not.

### Database level — constraints

| Rule | Constraint |
|---|---|
| Quantity never negative | `CHECK (quantity >= 0)` |
| One stock row per branch and product | `UNIQUE (branch_id, product_id)` |
| Admin has no branch, common user has one | `CHECK` on `users` |
| Stock references a real branch | `FOREIGN KEY` + `PRAGMA foreign_keys=ON` |

The database layer exists to make the rule **impossible to violate**, regardless of the
path taken, a route we have not written yet, a maintenance script, a direct SQL console,
or a second service reading the same file.

### Why both

They are not redundant; they answer different questions.

Application validation answers *"what should we tell the user?"* it runs before anything
is written and can explain itself. Database constraints answer *"what must always be
true?"* they run last and cannot be bypassed.

If only one could be kept, it would be the database constraint. A missing application check
produces an ugly error message; a missing database constraint produces corrupt data.

### Product existence — a special case

Checking that a SKU exists in the external catalog cannot be a database constraint: the
catalog is not in our database. It is validated in the application layer, on write
operations only, by calling the Product API before insertion.

This creates an asymmetry we adopted on purpose:

- **On read**, if the Product API is unavailable, we degrade gracefully, stock rows are
  displayed with raw SKUs instead of names, and the page stays usable.
- **On write**, if the Product API is unavailable, we refuse with a 503. We will not insert
  a product identifier we were unable to validate.