# 🔐 Système de Récupération de Mot de Passe - Guide Rapide

## Quoi de neuf ? ✨

Votre système de cantine a maintenant un **système sécurisé de récupération de mot de passe** :

```
Employé oublie son mot de passe
        ↓
Clique sur "Mot de passe oublié ?"
        ↓
Remplit : Code entreprise + Email
        ↓ 
Reçoit un lien par email (valide 24h)
        ↓
Clique le lien → affichage du formulaire de réinit
        ↓
Saisit nouveau mot de passe + confirmation
        ↓
Se reconnecte avec nouveau mot de passe ✅
```

---

## 🚀 Démarrage Rapide

### 1️⃣ Mise à jour du module **IMPORTANTE**

#### Via Terminal (Recommandé)

```bash
# Arrêtez votre Odoo actuel (Ctrl+C dans le terminal)

# Redémarrez Odoo avec upgrade
python -m odoo -c odoo.conf -d odoo18 -u lagunes_cantine

# Ou aller à Apps > lagunes_cantine > Upgrade
```

### 2️⃣ Configuration SMTP

**Pour tester localement :**

Option A - Avec MailHog (facile) :
```bash
# Téléchargez et lancez MailHog
mailhog
# Interface : http://localhost:8025
```

Ensuite, créez un serveur SMTP dans Odoo :
- Settings > Outgoing Mail Servers
- Ajouter : localhost:1025 (pas d'auth)

**Pour la production :**
- Configurez votre serveur SMTP réel (Gmail, O2Switch, etc.)
- Voir `RESET_PASSWORD_SETUP.md` pour les détails

### 3️⃣ Tester le système

1. Accédez à : `http://localhost:8069/cantine/forgot-password`
2. Remplissez avec vos données de test
3. Vérifiez l'email reçu
4. Cliquez le lien
5. Entrez un nouveau mot de passe
6. Connectez-vous !

---

## 📁 Fichiers Modifiés

```
custom_addons/lagunes_cantine/
├── models/
│   └── lagunes_employe.py           ✅ Nouvelles méthodes
├── controllers/
│   └── main.py                       ✅ Nouvelles routes
├── views/
│   └── website_templates.xml         ✅ Nouveaux templates + lien
│
└── Documentation/
    ├── RESET_PASSWORD_SETUP.md      📖 Config SMTP détaillée
    ├── INSTALLATION_TEST.md         🧪 Guide de test
    └── README_RESET_PASSWORD.md     📄 Ce fichier
```

---

## 🔗 URLs du Système

| URL | Accès | Description |
|-----|-------|-------------|
| `/cantine/forgot-password` | Public | Formulaire "Mot de passe oublié ?" |
| `/cantine/forgot-password/send` | API JSON | Traite la demande (backend) |
| `/cantine/forgot-password/reset/<token>` | Public | Formulaire de réinitialisation |
| `/cantine/forgot-password/reset/submit` | API JSON | Sauvegarde nouveau mot de passe |

---

## 📧 Configuration SMTP - Résumé

### Local (Test)

```
Host: localhost
Port: 1025
Sécurité: Aucune
User: (vide)
Password: (vide)

Utilisez MailHog (http://localhost:8025)
```

### Production - Gmail

```
Host: smtp.gmail.com
Port: 587
Sécurité: TLS
User: votre.email@gmail.com
Password: [mot de passe applicatif Google]
```

### Production - Serveur personnalisé

```
Host: smtp.votreserveur.com
Port: 587 ou 465
Sécurité: TLS ou SSL
User: votre.email@votredomaine.com
Password: votre_mot_de_passe
```

**Consulter `RESET_PASSWORD_SETUP.md` pour plus de détails (O2Switch, Scaleway, etc.)**

---

## 🔒 Sécurité

✅ **Implémenté :**
- Tokens uniques (32 caractères)
- Expiration après 24 heures
- Validation stricte du token
- Pas de révélation si email existe
- Token invalidé après utilisation

---

## 🐛 Troubleshooting Rapide

| Problème | Solution |
|----------|----------|
| 404 on `/cantine/forgot-password` | Redémarrez Odoo + upgrade |
| Email non reçu | Config SMTP, voir `RESET_PASSWORD_SETUP.md` |
| Token expiré | Normal après 24h, refaire la demande |
| Mot de passe non accepté | Minimum 4 caractères |

---

## 📞 Fichiers d'Aide

Consulter selon votre besoin :

- 🔧 **RESET_PASSWORD_SETUP.md** : Configuration SMTP complète
- 🧪 **INSTALLATION_TEST.md** : Guide de test détaillé  
- 📄 **README_RESET_PASSWORD.md** : Ce fichier (overview)

---

## ✅ Checklist Finale

- [ ] Module mis à jour (`python -m odoo ... -u lagunes_cantine`)
- [ ] Serveur SMTP configuré dans Odoo
- [ ] Test d'email envoyé (Settings > Outgoing Mail Servers > Envoyez test)
- [ ] Peut accéder à `/cantine/forgot-password`
- [ ] Email de réinit reçu avec lien cliquable
- [ ] Nouveau mot de passe défini
- [ ] Connexion réussie

---

## 🎉 Prêt !

Votre système de récupération de mot de passe est opérationnel !

**La prochaine étape ?** Tester sur votre serveur de production avec votre SMTP réel.

Pour questions : Consulter les fichiers `RESET_PASSWORD_SETUP.md` et `INSTALLATION_TEST.md`.

