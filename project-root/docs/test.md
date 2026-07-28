# HBntory — Tests et failles corrigées

Chaque membre de l'équipe documente ici les tests qu'il a effectués sur sa partie, et les failles/bugs identifiés puis corrigés. Un test = une ligne. Une faille = une ligne avec la correction associée.

---

## Soufiane Filali — Auth, sécurité, opérations stock, Backoffice

### Tests fonctionnels

- [ ] Login avec identifiants valides (admin) → session créée, `role` et `branch_id` renvoyés
- [ ] Login avec identifiants valides (common_user) → session créée, redirection vers vue stock
- [ ] Login avec mot de passe incorrect → 401, message générique
- [ ] Login avec compte désactivé (`is_active = False`) → 401, ne peut pas se connecter
- [ ] Logout → session invalidée
- [ ] Admin : lister les utilisateurs
- [ ] Admin : créer un utilisateur (common_user, rattaché à une branche)
- [ ] Admin : modifier la branche d'un utilisateur
- [ ] Admin : changer le mot de passe d'un utilisateur
- [ ] Admin : désactiver un compte (soft-delete)
- [ ] Admin : réactiver un compte désactivé
- [ ] Common user : ajouter du stock sur sa branche
- [ ] Common user : retirer du stock sur sa branche
- [ ] Common user : consulter le stock d'un produit sur sa branche
- [ ] Common user : lister tout le stock de sa branche
- [ ] Admin : vue globale du stock toutes branches confondues (lecture seule)

### Tests sécurité

- [ ] SQL injection sur les champs `username`/`password` du login
- [ ] IDOR : un common user tente d'accéder au stock d'une autre branche via modification de l'URL (`branch_id`) → 403
- [ ] Mass assignment : tentative d'injection de `role` ou `is_active` dans le body d'une requête de création d'utilisateur
- [ ] Type confusion : `quantity` envoyé comme string ou float au lieu d'un int → rejeté (400)
- [ ] Session après désactivation : un compte désactivé pendant qu'il a une session active perd l'accès à la requête suivante
- [ ] Un admin tente d'appeler une route stock (`POST /branches/<id>/stock`) → 403 (mauvais rôle)
- [ ] Un common user tente d'appeler une route utilisateurs (`GET /users`) → 403 (mauvais rôle)

### Failles trouvées et corrigées

- [ ] `branch_id` absent de la réponse `/login` → frontend recevait `undefined`, cassait le routage vers la vue stock et les appels stock ultérieurs (URL `/branches/undefined/stock`). Corrigé dans `routes/auth.py`.
- [ ] `PRODUCT_API_URL` pointait vers une URL Docker inexistante (`http://external-products-api:5000`) → toute validation de produit échouait silencieusement, faux message "Unknown product_id". Corrigé dans `app/config.py`.
- [ ] Route `PATCH /users/<id>/reactivate` absente alors que le frontend l'appelait → ajoutée, protégée par `role_required(Role.ADMIN)`.
- [ ] Base de données contenant d'anciens noms de branches ("Metro Paris Nord") non synchronisés avec le code → faisait échouer toute recherche de branche par nom côté agent IA. Corrigé par reset (`rm hbntory.db` + `python -m app.seed`).

---

## Sagal-Louise Haider — BDD, modèles SQLAlchemy, intégration Product API, interface admin (Claude Design)

### Tests fonctionnels

- [ ]
- [ ]
- [ ]

### Tests sécurité

- [ ]
- [ ]

### Failles trouvées et corrigées

- [ ]
- [ ]

---

## Noham Oulma — Product MCP Server, AI Query Service

### Tests fonctionnels

- [ ] `list_products` — listing paginé depuis l'API produit externe
- [ ] `get_product_details` — détails d'un produit valide
- [ ] `get_product_details` — identifiant invalide → erreur claire (pas de crash)
- [ ] `check_stock` — toutes branches confondues
- [ ] `check_stock` — restreint à une branche nommée
- [ ] `check_stock` — nom de branche inexistant → erreur claire, pas de tentative de deviner un autre nom
- [ ] `list_branch_stock` — liste du stock d'une branche
- [ ] `check_shopping_list` — liste satisfaisable dans au moins une branche
- [ ] `check_shopping_list` — liste non satisfaisable nulle part
- [ ] Chat public : question hors périmètre (ni produit, ni stock, ni branche) → refus poli, aucun tool appelé
- [ ] Chat public : question avec quantité → utilise bien `check_shopping_list`, jamais `check_stock` seul

### Tests sécurité

- [ ] Product API down pendant un appel → message d'erreur clair, pas de crash du serveur MCP
- [ ] Retry automatique sur erreur API Groq transitoire (jusqu'à `MAX_API_RETRIES`)
- [ ] Rate limit Groq atteint → message utilisateur clair, pas de fuite d'erreur technique brute

### Failles trouvées et corrigées

- [ ] `check_stock` avec `branch_name` échouait systématiquement (`No branch found with name 'HBntory Paris'`) alors que le nom de branche fourni était correct → cause réelle : base de données locale non resynchronisée avec les nouveaux noms de branches (voir section Soufiane). Pas un bug de `tools/stock.py`.
- [ ]
- [ ]

---

## Notes générales

- Toute case cochée `[x]` doit être accompagnée d'une brève précision si le test a révélé un comportement inattendu, même mineur.
- Une faille "trouvée et corrigée" doit toujours préciser : le symptôme observé, la cause réelle identifiée, et le fichier corrigé.
- Ce fichier est vivant : à mettre à jour au fil de l'eau, pas seulement avant une soutenance.