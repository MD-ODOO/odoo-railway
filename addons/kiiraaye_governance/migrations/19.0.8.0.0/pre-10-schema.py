import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    # The field is part of the new registry. Create the SQL columns early so an
    # existing database can be upgraded even if its previous module version did
    # not create them correctly.
    for column in ("kiiraaye_geographie_id", "kiiraaye_poste_id"):
        if not _column_exists(cr, "res_users", column):
            cr.execute(f"ALTER TABLE res_users ADD COLUMN {column} integer")
            _logger.info("Created res_users.%s", column)
