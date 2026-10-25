# Les bons comptes

Application Django pour gérer des porte-monnaies communs, ajouter des dépenses et partager les frais entre plusieurs membres.

## Installation

Prérequis : Python 3.12 et PowerShell sous Windows.

Dans le dossier contenant `manage.py`, exécuter :

```
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Ouvrir ensuite http://127.0.0.1:8000/.

Pour créer un compte administrateur :

```
python manage.py createsuperuser
```

L'administration est accessible sur http://127.0.0.1:8000/admin/.

Sous Linux ou macOS, les commandes équivalentes sont :

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Si `pip` refuse de lire `requirements.txt` (fichier encodé en UTF-16), installer directement les dépendances :

```
pip install Django==6.1.2 djangorestframework==3.18.3
```

## Fonctionnalités

- Création de compte et connexion avec une adresse e-mail.
- Gestion du profil et du mot de passe.
- Création et gestion de porte-monnaies communs.
- Invitation de membres par e-mail.
- Ajout et gestion des dépenses.
- Répartition des dépenses entre les membres.
- Clôture du porte-monnaie : liste des comptes qui doivent donner et de ceux qui doivent recevoir.
- Calcul de qui donne combien à qui, en minimisant le nombre de virements.
- Remboursements simulés (mock) entre membres.
- Mise à jour automatique de la page d'un porte-monnaie quand un autre membre ajoute ou supprime une dépense.
- API REST pour la gestion des comptes.

## Structure du projet

- `accounts/` : comptes et authentification.
- `wallets/` : porte-monnaies, membres et invitations.
- `expenses/` : dépenses.
- `the_good_accounts/` : configuration Django.
- `templates/` : pages HTML.
- `manage.py` : commandes Django.
- `requirements.txt` : dépendances Python.

## Routes principales

| URL | Vue | Rôle |
| --- | --- | --- |
| `/wallets/` | `wallet_list` | Mes porte-monnaies et invitations reçues |
| `/wallets/create/` | `wallet_create` | Créer un porte-monnaie (POST) |
| `/wallets/invitations/<id>/accept/` | `invitation_accept` | Accepter une invitation (POST) |
| `/wallets/<id>/` | `wallet_detail` | Détail, ajout de dépense, invitation |
| `/wallets/<id>/close/` | `wallet_close` | Clôturer le porte-monnaie (POST) |
| `/wallets/<id>/live/` | `wallet_live` | Rafraîchissement automatique (JSON) |
| `/wallets/<id>/reimburse/` | `reimburse` | Remboursement simulé (POST) |
| `/expenses/<id>/delete/` | `expense_delete` | Supprimer une dépense (POST) |
| `/register/`, `/login/`, `/logout/`, `/profile/`, `/password/` | `accounts` | Gestion du compte |
| `/api/v1/auth/...` | API REST | Inscription, connexion, profil |

## Faire les comptes

Le calcul se trouve dans `wallets/settlement.py`.

1. **Soldes** (`compute_balances`) : chaque membre doit une part égale du total. Le solde d'un membre est ce qu'il a payé moins sa part (positif : il doit recevoir, négatif : il doit donner). Les calculs sont faits en centimes ; les centimes restants de la division sont attribués aux premiers membres, si bien que la somme des soldes vaut toujours exactement 0. Une dépense sans payeur est attribuée à son créateur.
2. **Virements** (`minimize_transfers`) : on règle d'abord les paires dont la dette et la créance sont identiques (un seul virement pour deux personnes), puis on associe à chaque fois le plus gros débiteur au plus gros créancier. On obtient au plus `n - 1` virements, en `O(n log n)`. Trouver le minimum absolu est un problème NP-difficile, cette heuristique est la solution habituelle.
3. **Remboursement simulé** (`reimburse`) : sur un porte-monnaie clos, un débiteur voit un bouton « Rembourser (simulé) » sur ses virements. Le montant est recalculé côté serveur (il ne vient jamais du formulaire) et enregistré dans le modèle `Reimbursement`. Les remboursements sont pris en compte dans les soldes, donc le virement disparaît de la liste.

## Mise à jour dynamique

La page d'un porte-monnaie interroge `/wallets/<id>/live/?v=<version>` toutes les 3 secondes. La version est une empreinte (nombre de dépenses, dernier identifiant, total, clôture, membres, invitations, remboursements) :

- si rien n'a changé, le serveur répond `204` sans contenu, ce qui reste très léger ;
- sinon il renvoie le fragment HTML `templates/wallets/_live.html` mis à jour, qui remplace la partie dynamique de la page. Les formulaires ne sont pas touchés, donc une saisie en cours n'est pas perdue ;
- si le porte-monnaie vient d'être clôturé par un autre membre, la page est rechargée ;
- les onglets en arrière-plan n'interrogent pas le serveur.

Une alternative plus « temps réel » serait les WebSockets avec Django Channels, mais cela demande un serveur ASGI et Redis ; le polling suffit pour ce projet.

## Tester avec plusieurs comptes

La connexion repose sur un cookie de session : tous les onglets d'un même navigateur partagent donc le même compte. Pour tester avec plusieurs utilisateurs en même temps, utiliser une fenêtre de navigation privée ou un autre navigateur pour chaque compte.

## Tests

Pour vérifier le projet :

```
python manage.py check
python manage.py test
```