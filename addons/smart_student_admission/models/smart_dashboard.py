# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class SmartDashboard(models.Model):
    _name = "smart.dashboard"
    _description = "Tableau de bord SMART"

    name = fields.Char(default="Tableau de bord SMART", required=True)

    @api.model
    def open_dashboard(self):
        self._check_access()
        return {
            "type": "ir.actions.client",
            "tag": "smart_student_dashboard",
            "name": _("Tableau de bord SMART"),
        }

    @api.model
    def _check_access(self):
        if not self.env.user.has_group("smart_student_admission.group_smart_user"):
            raise AccessError(_("Vous n'avez pas accès au tableau de bord SMART."))

    @api.model
    def get_dashboard_data(self, filters=None):
        self._check_access()
        filters = filters or {}
        academic_year_id = filters.get("academic_year_id")
        package_id = filters.get("package_id")

        domain_sql = ["state != 'cancelled'"]
        params = []
        if academic_year_id:
            domain_sql.append("academic_year_id = %s")
            params.append(int(academic_year_id))
        if package_id:
            domain_sql.append("package_id = %s")
            params.append(int(package_id))

        where = " AND ".join(domain_sql)
        cr = self.env.cr

        cr.execute(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE state IN ('preinscription', 'visa', 'visa_obtained', 'completed')
                ) AS preinscription_obtained,
                COUNT(*) FILTER (
                    WHERE state IN ('visa_obtained', 'completed')
                ) AS visa_obtained
            FROM smart_student_application
            WHERE {where}
        """, params)
        row = cr.dictfetchone() or {}
        total = int(row.get("total") or 0)
        preinscription_obtained = int(row.get("preinscription_obtained") or 0)
        visa_obtained = int(row.get("visa_obtained") or 0)

        def pct(value):
            return round((value / total) * 100, 2) if total else 0.0

        cr.execute("""
            SELECT DISTINCT y.id, y.name, y.state
            FROM smart_academic_year y
            JOIN smart_student_application a ON a.academic_year_id = y.id
            WHERE a.state != 'cancelled'
            ORDER BY y.date_start DESC, y.name DESC
        """)
        academic_years = [
            {"id": int(r["id"]), "name": r["name"], "state": r["state"]}
            for r in cr.dictfetchall()
        ]

        cr.execute("""
            SELECT DISTINCT p.id, p.name
            FROM smart_service_package p
            JOIN smart_student_application a ON a.package_id = p.id
            WHERE a.state != 'cancelled'
            ORDER BY p.name
        """)
        package_options = [
            {"id": int(r["id"]), "name": r["name"]}
            for r in cr.dictfetchall()
        ]

        # Classement des formules sur le périmètre sélectionné.
        cr.execute(f"""
            SELECT
                a.package_id,
                COALESCE(p.name, 'Formule non renseignée') AS package_name,
                COUNT(*) AS count
            FROM smart_student_application a
            LEFT JOIN smart_service_package p ON p.id = a.package_id
            WHERE {where}
            GROUP BY a.package_id, p.name
            ORDER BY count DESC, package_name
        """, params)
        package_rows = []
        for item in cr.dictfetchall():
            count = int(item["count"] or 0)
            package_rows.append({
                "id": int(item["package_id"]) if item["package_id"] else False,
                "name": item["package_name"],
                "count": count,
                "percentage": round((count / total) * 100, 2) if total else 0.0,
            })

        top_package = package_rows[0] if package_rows else {
            "id": False,
            "name": _("Aucune formule renseignée"),
            "count": 0,
            "percentage": 0.0,
        }

        return {
            "filters": {
                "academic_years": academic_years,
                "packages": package_options,
                "selected_academic_year_id": int(academic_year_id) if academic_year_id else False,
                "selected_package_id": int(package_id) if package_id else False,
            },
            "kpis": {
                "total_dossiers": total,
                "preinscription_obtained": preinscription_obtained,
                "visa_obtained": visa_obtained,
                "preinscription_pct": pct(preinscription_obtained),
                "visa_pct": pct(visa_obtained),
            },
            "top_package": top_package,
            "packages": package_rows[:10],
        }
