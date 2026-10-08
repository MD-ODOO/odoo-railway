# -*- coding: utf-8 -*-
"""Migration des informations tenant.profile vers les contrats de location."""

from odoo import api, SUPERUSER_ID


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


def _column_exists(cr, table_name, column_name):
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        LIMIT 1
    """, (table_name, column_name))
    return bool(cr.fetchone())
