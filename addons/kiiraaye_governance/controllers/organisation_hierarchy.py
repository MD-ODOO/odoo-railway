from odoo import http
from odoo.http import request


class KiiraayeOrganisationHierarchyController(http.Controller):
    _managers_level = 5

    def _get_organisation(self, organisation_id, **kw):
        organisation_id = int(organisation_id) if organisation_id else False
        Organisation = request.env["kiiraaye.organisation"]
        organisation = Organisation.browse(organisation_id)
        return organisation if organisation.has_access("read") else Organisation.browse()

    def _prepare_organisation_data(self, organisation):
        type_record = organisation.type_id.sudo()
        return {
            "id": organisation.id,
            "name": organisation.name,
            "code": organisation.code or "",
            "type_name": type_record.name or "",
            "niveau": organisation.niveau or 0,
            "member_count": organisation.member_count or 0,
        }

    @http.route("/kiiraaye/get_org_chart", type="jsonrpc", auth="user")
    def get_org_chart(self, organisation_id, new_parent_id=None, **kw):
        organisation = self._get_organisation(organisation_id, **kw)
        if not organisation:
            return {
                "managers": [],
                "children": [],
            }

        context = kw.get("context") or {}
        max_level = context.get("max_level") or self._managers_level

        ancestors = []
        current_parent = (
            self._get_organisation(new_parent_id, **kw)
            if new_parent_id is not None
            else organisation.parent_id
        )

        while (
            current_parent
            and current_parent != organisation
            and current_parent not in ancestors
            and len(ancestors) < max_level
        ):
            ancestors.append(current_parent)
            current_parent = current_parent.parent_id

        children = organisation.child_ids.filtered(lambda child: child.active)

        return {
            "self": self._prepare_organisation_data(organisation),
            "managers": [
                self._prepare_organisation_data(parent)
                for parent in reversed(ancestors)
            ],
            "managers_more": bool(current_parent),
            "children": [
                self._prepare_organisation_data(child)
                for child in children
            ],
        }
