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

## Fonctionnalités

- Création de compte et connexion avec une adresse e-mail.
- Gestion du profil et du mot de passe.
- Création et gestion de porte-monnaies communs.
- Invitation de membres par e-mail.
- Ajout et gestion des dépenses.
- Répartition des dépenses entre les membres.
- API REST pour la gestion des comptes.

## Structure du projet

- `accounts/` : comptes et authentification.
- `wallets/` : porte-monnaies, membres et invitations.
- `expenses/` : dépenses.
- `the_good_accounts/` : configuration Django.
- `templates/` : pages HTML.
- `manage.py` : commandes Django.
- `requirements.txt` : dépendances Python.

## Tests

Pour vérifier le projet :

```
python manage.py check
python manage.py test
```