# HBntory — Approche UI/Backend

## 1. Deux interfaces, deux publics, aucun partage d'état

Le projet expose délibérément deux frontends séparés, servis indépendamment, qui ne partagent ni session ni logique de rendu :

- **`admin/`** — Backoffice authentifié, réservé aux employés et à l'admin
- **`client_web/`** — site public, sans authentification, catalogue + chat IA

Ce choix évite qu'une seule interface porte deux logiques d'autorisation différentes (authentifié vs anonyme), ce qui aurait multiplié les conditions et les risques d'erreur d'affichage d'un bouton ou d'une donnée à la mauvaise personne.

## 2. Stack frontend

Les deux frontends sont écrits en HTML/CSS/JS vanilla, avec un moteur de rendu maison (`support.js`, dc-runtime) qui interprète un template `<x-dc>` : bindings `{{ }}`, conditionnelles `<sc-if>`, boucles `<sc-for>`, gestion d'état via une classe `Component extends DCLogic` avec `state`, `setState`, et `renderVals()` qui recalcule les valeurs exposées au template à chaque changement d'état.

Pas de framework (React, Vue) côté build : tout tourne dans un seul fichier `index.html` par interface, chargé directement par le navigateur. Ce choix a été fait pour rester simple à déployer en local (pas de `npm install`, pas de bundler) dans le cadre du projet.

## 3. Backend : API REST Flask

Le Backoffice (`backoffice/`) est une API REST Flask classique :
- Blueprints par domaine (`auth_bp`, `stock_bp`, `users_bp`)
- SQLAlchemy pour l'ORM, SQLite comme base de développement
- Flask-Login pour la session, bcrypt pour le hachage des mots de passe
- flask-cors pour autoriser les requêtes cross-origin depuis les frontends servis sur des ports différents

Chaque route retourne du JSON structuré (`{"status": "success"/"error", ...}`), jamais de HTML. Le frontend ne fait que du `fetch()` avec `credentials: 'include'` pour transmettre le cookie de session.

## 4. Où vit la logique métier

La règle appliquée dans tout le projet : **le frontend n'est qu'une couche d'affichage et de saisie, jamais une couche de décision**.

Concrètement :
- Le frontend peut masquer un bouton "Créer un utilisateur" pour un common user, mais ce n'est qu'un confort d'affichage — la route `POST /users` refuse quand même la requête côté serveur si le rôle ne correspond pas
- La validation de quantité (`quantity > 0`, entier) est refaite côté serveur même si le frontend valide déjà le formulaire
- Le nom de branche affiché dans l'UI (résolu depuis un ID) est une commodité d'affichage ; l'autorisation réelle compare toujours l'ID de branche du compte connecté à celui de la ressource demandée, jamais le nom

Cette séparation est documentée en détail dans `docs/authentication.md`.

## 5. Communication frontend/backend : REST, sans état conservé

Toutes les interactions (login, gestion stock, gestion utilisateurs, chat IA) passent par des appels REST classiques, sans WebSocket. Le chat IA en particulier est stateless : chaque question envoyée à `POST /ask` est traitée indépendamment, sans historique de conversation conservé côté serveur entre deux questions. Ce choix simplifie le déploiement (pas de gestion de connexion persistante) et convient au cas d'usage (questions ponctuelles, pas de dialogue multi-tours nécessaire).

## 6. Approche des erreurs réseau côté frontend

Chaque appel `fetch()` passe par une méthode `api()` centralisée qui distingue trois cas :
- Succès (`res.ok`) → mise à jour du state, toast de confirmation
- Erreur métier renvoyée par le serveur (4xx avec un message JSON) → affichage du message d'erreur exact renvoyé par le backend, pas un message générique
- Échec réseau complet (serveur injoignable, timeout) → message générique "Le serveur ne répond pas", distinct du cas précédent

Cette distinction a été utile en debug : un bug qui ressemblait à une déconnexion aléatoire s'est avéré être un rechargement de page causé par l'outil de développement (Live Server) plutôt qu'un vrai problème de session — la distinction claire entre erreur réseau et erreur métier dans les logs a permis de l'isoler rapidement.

## 7. Ce qui n'est pas dans le frontend

Aucune information produit (nom, prix, description) n'est codée en dur ou mise en cache côté frontend au-delà de l'affichage courant : chaque page recharge les données depuis l'API produit externe ou depuis la base de stock locale à chaque visite. Voir `docs/architecture.md`, section 3, pour la règle d'or sur la séparation produit/stock.