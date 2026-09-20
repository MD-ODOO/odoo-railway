# Kiiraaye Gouvernance — Odoo 19

Base initiale de la refonte générale :

- `res.country` comme référentiel pays Odoo.
- `kiiraaye.geographie` pour la hiérarchie géographique mondiale, avec conservation de la désignation administrative locale.
- `kiiraaye.section` pour les sections/coordinations.
- membres simples liés aux sections.
- membres du bureau liés à des postes prédéfinis.
- siège géré par `res.partner` afin d'utiliser la structure d'adresse native d'Odoo.

Cette version vise Odoo 19 et n'utilise pas les anciennes constructions `_sql_constraints`, `name_get`, `<tree>`, `attrs` ou `states` de vues.

## Références techniques Odoo 19

Le module est aligné sur la documentation Odoo 19 actuelle :

- ORM : https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- Contraintes : https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/10_constraints.html
- Architectures de vues : https://www.odoo.com/documentation/19.0/developer/reference/user_interface/view_architectures.html
- Actions : https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- Sécurité : https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- Manifestes : https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html


Compatibilité Odoo 19 : res.groups.privilege/privilege_id, models.Constraint, vues list, expressions de vues modernes.

## Envoi des e-mails Odoo avec Resend

Le conteneur Odoo est prêt à utiliser Resend comme serveur SMTP par défaut. La configuration est chargée au démarrage depuis les variables d’environnement ; aucune clé Resend n’est stockée dans Git.

Variables à définir dans Railway :

```text
RESEND_API_KEY=re_xxxxxxxxx
RESEND_FROM_EMAIL=notifications@votre-domaine-verifie.tld
```

Variables optionnelles :

```text
RESEND_SMTP_HOST=smtp.resend.com
RESEND_SMTP_PORT=465
RESEND_SMTP_USER=resend
RESEND_SMTP_SSL=true
RESEND_FROM_FILTER=votre-domaine-verifie.tld
```

`RESEND_API_KEY` est utilisée comme mot de passe SMTP. Resend documente le serveur `smtp.resend.com`, l’utilisateur `resend` et le port sécurisé 465. Le domaine utilisé dans `RESEND_FROM_EMAIL` doit être configuré/autorisé dans Resend pour l’envoi de production.

Après définition des variables, redéployer le service Odoo puis effectuer un envoi de test depuis **Paramètres → Technique → Serveurs de messagerie sortants** ou depuis une fonctionnalité Odoo qui envoie un e-mail.

Pour remplacer une ancienne configuration SMTP Odoo enregistrée en base, le serveur sortant existant doit être désactivé ou configuré avec Resend ; Odoo peut privilégier un serveur sortant configuré en base avant le SMTP par défaut du processus.
