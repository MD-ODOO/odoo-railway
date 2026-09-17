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
