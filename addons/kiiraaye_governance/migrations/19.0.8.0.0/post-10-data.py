import logging

_logger = logging.getLogger(__name__)


def table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column),
    )
    return bool(cr.fetchone())


def set_column_not_null(cr, table, column):
    if table_exists(cr, table) and column_exists(cr, table, column):
        cr.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET NOT NULL')


def migrate(cr, version):
    # Legacy databases can contain rows created before the fields became required.
    # We repair only records that are structurally unusable; valid records remain untouched.
    # A fallback Senegal geography is used for legacy geo-scoped objects when available.
    senegal_id = None
    if table_exists(cr, "res_country") and table_exists(cr, "kiiraaye_geographie"):
        cr.execute("SELECT id FROM res_country WHERE code='SN' LIMIT 1")
        row = cr.fetchone()
        if row:
            cr.execute(
                "SELECT id FROM kiiraaye_geographie WHERE country_id=%s AND niveau='pays' AND parent_id IS NULL LIMIT 1",
                (row[0],),
            )
            root = cr.fetchone()
            if root:
                senegal_id = root[0]

    if senegal_id:
        for table in (
            "kiiraaye_activite", "kiiraaye_resultat", "kiiraaye_election",
            "kiiraaye_formation", "kiiraaye_plan_action", "kiiraaye_reunion",
            "kiiraaye_indicateur",
        ):
            if table_exists(cr, table) and column_exists(cr, table, "geographie_id"):
                cr.execute(f'UPDATE "{table}" SET geographie_id=%s WHERE geographie_id IS NULL', (senegal_id,))

        # Legacy sections without the new refonte fields are preserved and made explicit.
        if table_exists(cr, "kiiraaye_section"):
            if column_exists(cr, "kiiraaye_section", "type_section"):
                cr.execute("UPDATE kiiraaye_section SET type_section='nationale' WHERE type_section IS NULL")
            if column_exists(cr, "kiiraaye_section", "lieu_id"):
                cr.execute("UPDATE kiiraaye_section SET lieu_id=%s WHERE lieu_id IS NULL", (senegal_id,))

    # Orphaned hierarchy rows cannot represent valid governance records.
    if table_exists(cr, "kiiraaye_bureau") and column_exists(cr, "kiiraaye_bureau", "section_id"):
        cr.execute("DELETE FROM kiiraaye_bureau WHERE section_id IS NULL")
    if table_exists(cr, "kiiraaye_poste") and column_exists(cr, "kiiraaye_poste", "bureau_id"):
        cr.execute("DELETE FROM kiiraaye_poste WHERE bureau_id IS NULL")

    # Remove transient wizard rows that may carry stale NULLs from an earlier schema.
    if table_exists(cr, "kiiraaye_geo_import_wizard") and column_exists(cr, "kiiraaye_geo_import_wizard", "boundary_type"):
        cr.execute("DELETE FROM kiiraaye_geo_import_wizard WHERE boundary_type IS NULL")

    # Ensure all currently required fields have the database-level constraint.
    required_map = {
        "kiiraaye_geographie": ["name", "code", "niveau", "country_id"],
        "kiiraaye_section": ["type_section", "lieu_id"],
        "kiiraaye_bureau": ["section_id"],
        "kiiraaye_activite": ["geographie_id"],
        "kiiraaye_resultat": ["campagne_id", "geographie_id"],
        "kiiraaye_election": ["geographie_id"],
        "kiiraaye_formation": ["geographie_id"],
        "kiiraaye_plan_action": ["geographie_id"],
        "kiiraaye_reunion": ["geographie_id"],
        "kiiraaye_indicateur": ["geographie_id"],
    }
    for table, cols in required_map.items():
        for col in cols:
            set_column_not_null(cr, table, col)

    _logger.info("Kiiraaye 19.0.8 migration completed")
