# -*- coding: utf-8 -*-
"""Migration des informations tenant.profile vers les contrats de location."""

def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE imobilier_sn_contract AS c
           SET marital_situation = CASE
               WHEN lower(trim(p.social_situation)) IN (
                   'marie', 'marié', 'mariée', 'maries', 'mariés', 'mariee'
               ) THEN 'married'
               WHEN lower(trim(p.social_situation)) IN (
                   'celibataire', 'célibataire', 'celibataires', 'célibataires'
               ) THEN 'single'
               ELSE NULL
           END,
               profession = p.profession,
               source_income = p.source_income,
               salary_bulletin = p.salary_bulletin,
               salary_bulletin_filename = p.salary_bulletin_filename,
               other_income_document = p.other_income_document,
               other_income_document_filename = p.other_income_document_filename,
               client_notes = p.notes
          FROM (
              SELECT DISTINCT ON (partner_id)
                     partner_id,
                     social_situation,
                     profession,
                     source_income,
                     salary_bulletin,
                     salary_bulletin_filename,
                     other_income_document,
                     other_income_document_filename,
                     notes
                FROM imobilier_sn_tenant_profile
               ORDER BY partner_id, id DESC
          ) AS p
         WHERE c.contract_type = 'rent'
           AND c.customer_id = p.partner_id
    """)

    cr.execute("""
        UPDATE res_partner AS rp
           SET is_imobilier_tenant = TRUE
         WHERE EXISTS (
             SELECT 1
               FROM imobilier_sn_contract AS c
              WHERE c.contract_type = 'rent'
                AND c.customer_id = rp.id
         )
            OR EXISTS (
             SELECT 1
               FROM imobilier_sn_tenant_profile AS p
              WHERE p.partner_id = rp.id
         )
    """)

    if _column_exists(cr, "res_partner", "customer_rank"):
        cr.execute("""
            UPDATE res_partner AS rp
               SET customer_rank = GREATEST(COALESCE(rp.customer_rank, 0), 1)
             WHERE rp.is_imobilier_tenant = TRUE
        """)

    cr.execute("""
        UPDATE res_partner AS rp
           SET is_imobilier_owner = TRUE
         WHERE EXISTS (
             SELECT 1
               FROM imobilier_sn_property AS p
              WHERE p.owner_id = rp.id
         )
    """)

    if _column_exists(cr, "res_partner", "supplier_rank"):
        cr.execute("""
            UPDATE res_partner AS rp
               SET supplier_rank = GREATEST(COALESCE(rp.supplier_rank, 0), 1)
             WHERE rp.is_imobilier_owner = TRUE
        """)


    # Nettoyage de l'ancien modèle tenant.profile après migration des données.
    cr.execute("""
        DELETE FROM ir_model_access
         WHERE model_id IN (
             SELECT id FROM ir_model
              WHERE model = 'imobilier.sn.tenant.profile'
         )
    """)
    cr.execute("""
        DELETE FROM ir_ui_view
         WHERE model = 'imobilier.sn.tenant.profile'
    """)
    cr.execute("""
        DELETE FROM ir_actions
         WHERE id IN (
             SELECT res_id
               FROM ir_model_data
              WHERE module = 'imobilier_sn'
                AND model = 'ir.actions.act_window'
                AND name = 'action_imobilier_sn_tenant'
         )
    """)
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'imobilier_sn'
           AND name IN (
               'view_imobilier_sn_tenant_profile_list',
               'view_imobilier_sn_tenant_profile_form',
               'action_imobilier_sn_tenant'
           )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model_id IN (
             SELECT id FROM ir_model
              WHERE model = 'imobilier.sn.tenant.profile'
         )
    """)
    cr.execute("""
        DELETE FROM ir_model
         WHERE model = 'imobilier.sn.tenant.profile'
    """)
    cr.execute("DROP TABLE IF EXISTS imobilier_sn_tenant_profile CASCADE")


def _column_exists(cr, table_name, column_name):
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        LIMIT 1
    """, (table_name, column_name))
    return bool(cr.fetchone())
