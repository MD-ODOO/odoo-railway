# Kiiraaye Governance V5 — Odoo 19 Community

## V5
- Bouton « Imprimer carte de membre » directement sur la fiche partisan.
- Création automatique d'une carte si aucune carte active/non annulée n'existe.
- Référence automatique.
- QR Code sécurisé contenant une URL de vérification.
- Jeton unique de vérification.
- Page publique de vérification de la validité de la carte.
- La vérification publique n'expose pas le N° ID national.
- Carte PDF conservant le logo de la société Odoo comme filigrane.
- Photo, matricule, section, territoire et fonction sur la carte.

## Mise à jour
```bash
./odoo-bin -d votre_base -u kiiraaye_governance --stop-after-init
```
