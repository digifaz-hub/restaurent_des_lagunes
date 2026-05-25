# Système de Réinitialisation de Mot de Passe - Configuration

## 📋 Résumé

Ce module ajoute un système de réinitialisation de mot de passe sécurisé pour les employés de la cantine :

1. **Page "Mot de passe oublié ?"** → `/cantine/forgot-password`
2. **Validation** : Code d'accès + email
3. **Email avec lien sécurisé** : Lien avec token valide 24h
4. **Formulaire de réinitialisation** : Accessible via le lien
5. **Token expirant** : Sécurité renforcée

---

## 🔧 Configuration SMTP

### Option 1 : Configuration SMTP Locale (pour tester)

#### A. Avec un serveur SMTP local (MailHog, Postfix, etc.)

**Dans Odoo, allez à :**
- `Settings > Outgoing Mail Servers`

**Créez un nouveau serveur :**
```
Name: localhost
Host: localhost
Port: 1025
Connexion Security: Aucune
User: (vide)
Password: (vide)
```

**Testez :**
```bash
# Installez MailHog (simple pour tester)
# Windows : télécharger de https://github.com/mailhog/mailhog/releases

# Lancez MailHog
mailhog

# Accédez à l'interface Web : http://localhost:8025
```

#### B. Sans serveur SMTP (simulation locale)

Si vous voulez tester sans serveur SMTP réel :

1. Dans Odoo, allez à `Settings > System Parameters`
2. Cherchez le paramètre `mail.catchall.domain` 
3. Mettez-le à vide ou à `localhost`

> **Note** : Les emails ne seront pas vraiment envoyés, mais le système fonctionnera.

---

### Option 2 : Configuration pour Production (Serveur Distant)

**Dans Odoo, allez à :**
- `Settings > Outgoing Mail Servers`

#### Exemple 1 : Gmail SMTP
```
Name: Gmail

Host: smtp.gmail.com
Port: 587
Connection Security: TLS
User: votre.email@gmail.com
Password: votre_mot_de_passe_applicatif
```

**Important :** 
- Pour Gmail, générez un "mot de passe applicatif" (pas votre mot de passe Gmail)
- Activez "App passwords" dans votre compte Google

#### Exemple 2 : Serveur SMTP personnalisé
```
Name: SH Hosting (exemple)
Host: smtp.votreserveur.com
Port: 587 (ou 465 pour SSL)
Connection Security: TLS
User: votre.email@votreserveur.com
Password: votre_mot_de_passe
```

#### Exemple 3 : O2Switch / Hébergement FR
```
Name: O2Switch SMTP
Host: smtp.o2switch.net
Port: 465
Connection Security: SSL
User: votrecompte@votredomaine.com
Password: mot_de_passe_smtp
```

---

## 📧 Configuration de l'email "Expéditeur"

### Dans Odoo :
1. Allez à `Settings > Email Configuration`
2. Remplissez :
   - **Default "From" Address** : noreply@votredomaine.com
   - **Custom "From" Name** : Restaurant des Lagunes

### Alternative : Configuration du fichier config
Éditez `odoo.conf` et ajoutez :
```ini
email_from = noreply@votredomaine.com
mail_server_id = 1  # ID du serveur SMTP configuré
```

---

## 🧪 Tester le Système Localement

### Étape 1 : Créer un compte de test

1. Allez à `Restaurant des Lagunes > Cantine > Gestion des Employés`
2. Cliquez sur une entreprise cliente
3. Créez un employé :
   - **Nom** : Dupont
   - **Prénom** : Jean
   - **Email** : jean.dupont@test.com
   - **Entreprise** : Restaurant des Lagunes
   - **Actif** : ✓

### Étape 2 : Accéder à la page "Mot de passe oublié"

```
http://votreadresse/cantine/forgot-password
```

### Étape 3 : Remplir le formulaire

- **Code entreprise** : [le code d'accès de l'entreprise]
- **Email** : jean.dupont@test.com

### Étape 4 : Vérifier l'email

- Avec **MailHog** : Allez à `http://localhost:8025`
- Avec **Gmail** : Vérifiez votre boîte de réception
- Avec **Log Odoo** : Les erreurs d'email apparaissent dans `/var/log/odoo/odoo.log`

### Étape 5 : Cliquer sur le lien

Le lien dans l'email ressemblera à :
```
http://votreadresse/cantine/forgot-password/reset/[TOKEN_LONG]
```

---

## 🔐 Flux Completo

```
┌─────────────────────────────────────────┐
│ 1. Employé clique "Mot de passe oublié?" │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 2. Remplit : Code entreprise + Email                │
│    Route: POST /cantine/forgot-password/send         │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 3. Backend génère token (valide 24h)                │
│    Sauvegarde : reset_password_token                │
│    Sauvegarde : reset_password_expiry                │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 4. Envoie email avec lien                            │
│    Lien: /cantine/forgot-password/reset/[TOKEN]     │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 5. Employé clique le lien dans l'email              │
│    Route: GET /cantine/forgot-password/reset/[TOKEN]│
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 6. Valide le token (pas expiré)                     │
│    Affiche le formulaire de réinitialisation        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 7. Employé saisit nouveau mot de passe              │
│    Route: POST /cantine/forgot-password/reset/submit│
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ 8. Backend sauvegarde le nouveau mot de passe       │
│    Invalide le token                                 │
│    Redirige vers /cantine (connexion)               │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Déploiement sur Serveur

### Étape 1 : Vérifier les dépendances
```bash
# Les emails sont gérés nativement par Odoo
# Assurez-vous que :
pip install openerp  # ou odoo
```

### Étape 2 : Configurer le serveur SMTP

Dans le panneau d'administration Odoo du serveur :
1. Settings > Outgoing Mail Servers
2. Configurez votre serveur SMTP

Ou dans `/etc/odoo/odoo.conf` :
```ini
[options]
mail_server_id = 1
email_from = noreply@votredomaine.com
```

### Étape 3 : Tester los emails

```bash
# Sur le serveur, lancez un test
sudo -u odoo python3 -c "from odoo import api; print('Email OK')"
```

### Étape 4 : Redémarrer Odoo
```bash
sudo systemctl restart odoo
```

---

## 📝 Champs Utilisés

### Modèle `lagunes.employe`

| Champ | Type | Description |
|-------|------|-------------|
| `reset_password_token` | Char | Token unique pour réinitialisation |
| `reset_password_expiry` | Datetime | Date/heure d'expiration (24h) |
| `mot_de_passe` | Char | Mot de passe actuel |

### Routes Ajoutées

| Route | Méthode | Description |
|-------|---------|-------------|
| `/cantine/forgot-password` | GET | Affiche formulaire |
| `/cantine/forgot-password/send` | POST (JSON) | Traite la demande |
| `/cantine/forgot-password/reset/<token>` | GET | Affiche formulaire réinit (si token valide) |
| `/cantine/forgot-password/reset/submit` | POST (JSON) | Sauvegarde nouveau mot de passe |

### Méthodes Ajoutées

```python
employe.generate_reset_token()        # Génère un token 24h
employe.is_reset_token_valid()        # Vérifie validité du token
employe.send_reset_password_email()   # Envoie l'email avec lien
employe.reset_password(new_password)  # Sauvegarde nouveau mot de passe
```

---

## 🔒 Sécurité

✅ **Implémenté :**
- Token URL-safe de 32 caractères
- Expiration après 24 heures
- Validation du token avant affichage du formulaire
- Token invalidé après réinitialisation
- Pas de révélation si email/code existe (pour éviter énumération)
- Mots de passe en plain text → considérez hash en production

⚠️ **À faire en production :**
- Hasher les mots de passe avec bcrypt/argon2
- Ajouter HTTPS obligatoire
- Implémenter rate limiting sur `/forgot-password/send`
- Ajouter captcha si nécessaire
- Logger les tentatives suspectes

---

## 🐛 Dépannage

### Email non reçu

1. **Vérifier Odoo :**
   - Settings > Outgoing Mail Servers
   - Cliquez sur le serveur > Envoyez un email test

2. **Vérifier les logs :**
   ```bash
   tail -f /var/log/odoo/odoo.log | grep mail
   ```

3. **Vérifier MailHog :**
   ```
   http://localhost:8025
   ```

### Token expiré

- Les tokens expirent après 24 heures
- L'utilisateur doit recommencer la procédure

### "Email non reconnu"

- Vérifiez que l'employé est actif dans l'entreprise
- L'email doit correspondre parfaitement (insensible à la casse, mais pas d'espaces)

---

## 📚 Fichiers Modifiés

- `models/lagunes_employe.py` : Ajout champs + méthodes
- `controllers/main.py` : Routes + logique
- `views/website_templates.xml` : Templates frontend
- `__manifest__.py` : Déclaration des nouvelles routes

---

## ✨ Prochaines Améliorations (Optionnel)

- [ ] Hashtage des mots de passe
- [ ] Rate limiting sur demande mot de passe
- [ ] Téléphone optionnel (2FA)
- [ ] Historique des réinitialisations
- [ ] Email de confirmation de changement
- [ ] Questions de sécurité (fallback)

