# HBntory — Authentification et autorisation

## 1. Vue d'ensemble

Le Backoffice HBntory utilise une authentification par **session** (Flask-Login), avec des mots de passe hachés en **bcrypt**. Il n'y a pas de token JWT ni d'API key : après connexion, le navigateur reçoit un cookie de session signé, envoyé automatiquement à chaque requête suivante.

L'autorisation repose sur deux niveaux, tous deux vérifiés **côté serveur** : le rôle du compte (`Role`) et, pour les common users, la branche à laquelle ce compte est rattaché (`branch_id`). Aucune vérification de droits n'est faite côté frontend : masquer un bouton dans l'interface n'est jamais considéré comme un contrôle d'accès.

## 2. Modèle de données

Défini dans `backoffice/app/models.py`.

```python
class Role(enum.Enum):
    ADMIN = "admin"
    COMMON_USER = "common_user"
```

Table `users` :
- `username` — unique
- `password_hash` — bcrypt, jamais stocké en clair
- `role` — `ADMIN` ou `COMMON_USER`
- `branch_id` — clé étrangère vers `branches`, nullable
- `is_active` — booléen, utilisé pour le soft-delete

Une contrainte au niveau base de données garantit la cohérence rôle/branche :

```python
CheckConstraint(
    "(role = 'ADMIN' AND branch_id IS NULL) OR "
    "(role = 'COMMON_USER' AND branch_id IS NOT NULL)",
)
```

Un admin n'a jamais de branche. Un common user a toujours exactement une branche. Cette règle est appliquée dès la création du schéma, pas seulement en application.

`User` hérite de `UserMixin` (Flask-Login), ce qui fournit `get_id()`, `is_authenticated`, `is_active`, `is_anonymous` sans les redéfinir à la main.

## 3. Hachage des mots de passe

Dans `backoffice/routes/auth.py` :

```python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())
```

Le sel est généré automatiquement par `bcrypt.gensalt()` à chaque hachage — deux comptes avec le même mot de passe n'ont jamais le même hash stocké.

## 4. Connexion (`POST /login`)

1. Recherche de l'utilisateur par `username`
2. Rejet si l'utilisateur n'existe pas, si le mot de passe est incorrect, ou si le compte est désactivé (`is_active = False`) — dans tous les cas, le même message générique `"Invalid credentials"` est renvoyé (401), pour ne pas révéler si c'est le nom d'utilisateur ou le mot de passe qui est en cause
3. Si tout est valide, `login_user(user)` crée la session Flask-Login
4. La réponse renvoie `username`, `role`, et `branch_id` — ces trois champs permettent au frontend de savoir vers quelle vue router l'utilisateur (liste des utilisateurs pour un admin, vue stock pour un common user) sans avoir à interroger une deuxième route

## 5. Déconnexion (`POST /logout`)

Protégée par `@login_required`. Appelle `logout_user()`, qui invalide la session côté serveur.

## 6. Autorisation par rôle : `role_required`

Défini dans `backoffice/routes/middleware.py` :

```python
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
```

Utilisé en décorateur sur chaque route sensible, par exemple :

```python
@role_required(Role.ADMIN)
def list_users(): ...

@role_required(Role.COMMON_USER)
def add_stock(branch_id): ...
```

Deux cas d'échec distincts :
- Pas de session valide → 401 Unauthorized
- Session valide mais mauvais rôle → 403 Access denied

## 7. Autorisation par branche : `branch_required`

Toujours dans `middleware.py`, appliqué en complément de `role_required` sur les routes stock :

```python
def branch_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        branch_id = kwargs.get("branch_id")
        if current_user.branch_id != branch_id:
            return jsonify({"status": "error", "message": "Access denied"}), 403
        return f(*args, **kwargs)
    return wrapper
```

Compare le `branch_id` de l'URL (`/branches/<int:branch_id>/stock`) à celui du compte connecté. Un common user ne peut jamais agir sur le stock d'une autre branche que la sienne, même en modifiant l'URL manuellement.

## 8. Matrice de permissions par route

| Route | Méthode | Rôle requis | Contrainte branche |
|---|---|---|---|
| `/login` | POST | aucun | — |
| `/logout` | POST | authentifié | — |
| `/users` | GET, POST | ADMIN | — |
| `/users/<id>` | PATCH, DELETE | ADMIN | — |
| `/users/<id>/reactivate` | PATCH | ADMIN | — |
| `/branches/<id>/stock` | GET, POST | COMMON_USER | oui, sa branche uniquement |
| `/branches/<id>/stock/remove` | POST | COMMON_USER | oui, sa branche uniquement |
| `/branches/<id>/stock/<product_id>` | GET | COMMON_USER | oui, sa branche uniquement |
| `/products` | GET | COMMON_USER | — |
| `/stock` | GET | ADMIN | — (vue globale multi-branches, lecture seule) |

Un admin n'a accès à aucune route stock d'écriture. Un common user n'a accès à aucune route utilisateurs. Ce n'est pas une convention côté frontend : chaque route refuse explicitement l'appel si le rôle ne correspond pas.

## 9. Suppression de compte : soft-delete uniquement

`DELETE /users/<id>` ne supprime jamais la ligne en base. Il passe `is_active` à `False` :

```python
user.is_active = False
db.session.commit()
```

Un compte désactivé ne peut plus se connecter (vérifié à l'étape 2 du login), mais son historique (créations de stock passées, etc.) reste intact. `PATCH /users/<id>/reactivate` inverse l'opération.

## 10. Ce que l'autorisation ne couvre pas

- Pas de limitation de tentatives de connexion (pas de rate limiting sur `/login`) — hors périmètre de ce projet
- Pas d'expiration automatique de session au-delà du comportement par défaut de Flask-Login
- `SECRET_KEY` (utilisée pour signer les cookies de session) est définie en dur avec une valeur de développement dans `app/config.py`, à surcharger via la variable d'environnement `SECRET_KEY` dans un environnement de production

## 11. Frontière avec le site public

Le site public (`client_web/`) n'a **aucune authentification** et n'appelle jamais les routes du Backoffice. Il ne consulte que l'API produit externe (lecture seule) et l'agent IA, qui lui-même n'a accès qu'à des opérations de lecture sur le stock (jamais d'écriture) via les tools du serveur MCP. Aucune donnée de session, aucun cookie, aucun rôle n'existe côté site public.