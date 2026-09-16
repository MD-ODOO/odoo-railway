# Kiiraaye Gouvernance — V7 Refonte base

## Périmètre de cette version

Cette version refond le socle autour de deux objets :

1. **Référentiel géographique mondial**
   - `res.country` reste la table des pays Odoo.
   - `kiiraaye.geographie` porte les subdivisions : région/État/province, département/comté/district, commune/municipalité/ville, communauté rurale/niveau local, quartier/district de proximité, localité.
   - Chaque entrée est rattachée à un pays et à un parent.
   - Les niveaux administratifs réels d'origine sont conservés via `admin_level`.
   - Les champs `country_id` et `state_id` assurent la compatibilité avec le référentiel d'adresse Odoo.

2. **Section / Coordination**
   - Type : communale, départementale, régionale, nationale, diaspora.
   - `Lieu / Zone` pointe vers le bon niveau géographique selon le type.
   - National et diaspora utilisent le Sénégal par défaut lorsqu'il existe dans le référentiel.
   - Le siège utilise une structure d'adresse Odoo : rue, complément, code postal, ville, région/État, pays et zone géographique.
   - Deux onglets : Membres et Membres du bureau.
   - Un bureau de référence est créé automatiquement pour chaque section/coordination.
   - Les membres du bureau sont des attributions de postes.

## Données géographiques

Les pays sont initialisés automatiquement depuis `res.country` après installation.

Les subdivisions sont importables depuis geoBoundaries / gbOpen, une couche à la fois, via :

**Configuration > Géographie > Importer une couche administrative**

L'import peut utiliser la géométrie simplifiée ou la géométrie complète.

Source : https://www.geoboundaries.org/api.html
Licence de la couche gbOpen : selon les métadonnées fournies par geoBoundaries ; attribution requise.

## Ordre d'import recommandé

Pour un pays donné : ADM1, puis ADM2, puis ADM3, ADM4 et ADM5.

L'application conserve toujours le niveau source `ADM0...ADM5` afin de ne pas présenter les libellés français comme une équivalence universelle. Les significations des niveaux administratifs diffèrent selon les pays.
