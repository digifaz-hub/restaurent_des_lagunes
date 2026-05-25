# Installation et Test du Système de Récupération de Mot de Passe

## 🚀 Installation Rapide

### Étape 1 : Mise à jour du module

```bash
# Allez dans le répertoire de votre Odoo
cd /chemin/vers/odoo

# Redémarrez Odoo avec l'option de mise à jour
# Option A : Si vous utilisez un terminal Odoo actif
# Arrêtez le serveur : Ctrl+C
# Puis relancez avec l'option -d pour votre base de données :

python3 -m odoo -c odoo.conf -d odoo18 -m base  # Démarrage normal

# Option B : Via l'interface Odoo
# 1. Allez à Apps
# 2. Recherchez "lagunes_cantine"
# 3. Cliquez sur le module
# 4. Cliquez sur "Upgrade"
```

### Étape 2 : Vérifier l'installation

L'interface devrait afficher les champs supplémentaires dans le modèle `lagunes.employe` :
- `reset_password_token` (absent de la vue backend - champ technique)
- `reset_password_expiry` (absent de la vue backend - champ technique)

> **Note** : Ces champs sont techniques et ne s'affichent pas dans l'interface habituelle. C'est normal !

---

## 🧪 Test Complet du Système

### Prérequis

- ✅ Module `lagunes_cantine` activé
- ✅ Au moins une entreprise "Client Cantine" configurée
- ✅ Au moins un employé enregistré pour cette entreprise
- ✅ Serveur SMTP configuré (local ou distant)

---

### Test 1 : Page "Mot de passe oublié ?"

#### Étape 1a : Accéder à la page

Ouvrez votre navigateur et allez à :
```
http://localhost:8069/cantine/forgot-password
```

Ou si vous hébergez sur un serveur :
```
https://votredomaine.com/cantine/forgot-password
```

#### Résultat attendu

- 📄 Formulaire avec 2 champs :
  - Code entreprise (password input - masqué)
  - Adresse email

- 🔘 Un bouton "Envoyer le lien de réinitialisation"

- 🔗 Un lien "Retour à la connexion" en bas

---

### Test 2 : Demande de réinitialisation

#### Préparez les données de test

1. Allez à **Contacts > Cantine** (ou directement à votre entreprise)
2. Notez le **Code d'accès** (ex: `CODETEST123`)
3. Allez aux **Employés** et notez un email existant (ex: `test@example.com`)

#### Remplissez le formulaire

```
Code entreprise   : CODETEST123
Adresse email     : test@example.com
```

Cliquez sur **"Envoyer le lien de réinitialisation"**

#### Résultat attendu

✅ **Message de succès :**
```
"Un lien de réinitialisation a été envoyé à votre email. 
Il expire dans 24 heures."
```

⚠️ **Cas d'erreur (code d'accès invalide) :**
```
"Code d'accès incorrect."
```

⚠️ **Cas d'erreur (email invalide) :**
```
"Un lien de réinitialisation a été envoyé à votre email."
(Message identique pour des raisons de sécurité)
```

---

### Test 3 : Email de réinitialisation

#### Vérifier réception

**Avec MailHog (local) :**
```
http://localhost:8025
```
Vous devriez voir l'email dans l'interface MailHog.

**Avec votre email réel :**
- Allez à la boîte de réception
- Cherchez un email de "Restaurant des Lagunes"
- Sujet : "Réinitialisation de votre mot de passe"

#### Contenu attendu de l'email

```
Bonjour [Prénom Nom],

Vous avez demandé une réinitialisation de mot de passe 
pour votre compte cantine.

[BOUTON BLEU : "Réinitialiser mon mot de passe"]

Ce lien expire dans 24 heures.

Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.

Cordialement,
Restaurant des Lagunes
```

---

### Test 4 : Cliquer sur le lien

#### Résultat attendu

✅ Vous êtes redirigé vers une page de formulaire de réinitialisation :

```
Employé     : Jean Dupont
Entreprise  : Restaurant des Lagunes

Nouveau mot de passe     : [input password]
Confirmer le mot de passe : [input password]

[BOUTON VERT : "Réinitialiser le mot de passe"]
```

#### Cas d'erreur (lien expiré)

```
Erreur

Lien de réinitialisation invalide ou expiré. 
Veuillez recommencer.

[BOUTON : "Retour à l'accueil"]
```

---

### Test 5 : Entrer un nouveau mot de passe

#### Formulaire

```
Nouveau mot de passe        : MoiNouveauPassword123
Confirmer le mot de passe   : MoiNouveauPassword123
```

#### Résultat attendu

✅ **Succès :**
```
Message vert : "Mot de passe réinitialisé avec succès. 
               Connectez-vous maintenant."

L'écran se referme automatiquement après 2 secondes
et vous êtes redirigé vers /cantine (connexion)
```

#### Cas d'erreur : Mots de passe non identiques

```
Message rouge : "Les mots de passe ne correspondent pas."
```

#### Cas d'erreur : Mot de passe trop court

```
Message rouge : "Le mot de passe doit contenir au moins 4 caractères."
```

---

### Test 6 : Connexion avec nouveau mot de passe

#### Accédez à /cantine

```
http://localhost:8069/cantine
```

#### Connectez-vous

**Étape 1 :**
```
Code entreprise : CODETEST123
[Cliquez "Accéder au menu du jour"]
```

**Étape 2 :**
```
Adresse email     : test@example.com
Mot de passe      : MoiNouveauPassword123
[Cliquez "Valider et accéder"]
```

#### Résultat attendu

✅ Vous êtes connecté et voyez le menu du jour !

---

## 🔍 Dépannage

### Problème 1 : "Page non trouvée" (404)

**Cause possible :** Le module n'a pas été mis à jour.

**Solution :**
```bash
# Redémarrez Odoo avec update activé
python3 -m odoo -c odoo.conf -d odoo18 -u lagunes_cantine
```

### Problème 2 : Email non reçu

**Cause possible 1 :** Serveur SMTP non configuré

**Solution :**
1. Allez à `Settings > Outgoing Mail Servers`
2. Vérifiez qu'un serveur est configuré
3. Cliquez sur le serveur et envoyez un email de test

**Cause possible 2 :** Email bloqué en spam

**Solution :**
- Vérifiez votre dossier "Spam" ou "Promotions"
- Pour MailHog, l'email s'affiche toujours

### Problème 3 : "Token expiré"

**Cause (normale) :** Le lien avait plus de 24 heures

**Solution :**
- Refaites la demande de réinitialisation

### Problème 4 : Erreur JavaScript

Ouvrez la **console du navigateur** (F12 > Console) et cherchez des erreurs rouges.

---

## 📊 Logs pour Déboguer

### Consulter les logs Odoo

```bash
# Linux/Mac
tail -f /var/log/odoo/odoo.log

# Windows (PowerShell)
Get-Content "C:\logs\odoo\odoo.log" -Wait
```

### Chercher les erreurs d'email

```bash
grep -i "error\|mail\|email" odoo.log
```

---

## ✅ Checklist d'Installation Complète

- [ ] Module `lagunes_cantine` mis à jour (upgrade appliquée)
- [ ] Champs `reset_password_token` et `reset_password_expiry` ajoutés à la base de données
- [ ] Page `/cantine/forgot-password` accessible
- [ ] Serveur SMTP configuré
- [ ] Employé de test créé
- [ ] Email de test reçu
- [ ] Lien de réinitialisation cliquable
- [ ] Formulaire de réinitialisation affiché
- [ ] Nouveau mot de passe sauvegardé
- [ ] Connexion réussie avec nouveau mot de passe

---

## 📞 Support Supplémentaire

Si vous avez des problèmes :

1. Consultez `RESET_PASSWORD_SETUP.md` pour les configurations SMTP
2. Vérifiez les logs Odoo
3. Testez avec MailHog en local d'abord
4. Assurez-vous que le module a bien été mis à jour

