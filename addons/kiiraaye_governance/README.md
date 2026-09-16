# Kiiraaye Governance V6 — Odoo 19 Community

## Géographie
Le menu Territoires n'est plus exposé directement sous Organisation.
La gestion géographique est sous Configuration → Géographie.

Sources étudiées :
- geoBoundaries gbOpen : API ADM0 à ADM5, CC BY 4.0 recommandé par le projet pour gbOpen ;
- OpenStreetMap : hiérarchies admin_level variables selon les pays ;
- Sénégal : référence d'organisation territoriale du Ministère de l'Intérieur.

Le module initialise les pays à partir de `res.country` et importe les frontières
administratives par couche depuis geoBoundaries. La carte SVG/OWL affiche les
géométries GeoJSON importées.

Important : tous les pays n'ont pas les mêmes niveaux administratifs. ADM1-ADM5
sont donc conservés comme niveaux source et normalisés en niveaux Kiiraaye.
La disponibilité d'un niveau « quartier » n'est pas garantie pour chaque pays.

Mise à jour:
`./odoo-bin -d votre_base -u kiiraaye_governance --stop-after-init`
