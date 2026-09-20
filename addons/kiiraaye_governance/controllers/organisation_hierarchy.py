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


class KiiraayeSectionHierarchyController(http.Controller):
    _managers_level = 5

    def _get_section(self, section_id):
        try:
            section_id = int(section_id)
        except (TypeError, ValueError):
            return request.env["kiiraaye.section"].browse()

        Section = request.env["kiiraaye.section"]
        section = Section.browse(section_id).exists()
        return section if section.active else Section.browse()

    def _prepare_section_data(self, section):
        labels = dict(request.env["kiiraaye.section"]._fields["type_section"].selection)
        levels = {
            "nationale": 1,
            "regionale": 2,
            "departementale": 3,
            "communale": 4,
            "diaspora": 1,
        }
        return {
            "id": section.id,
            "name": section.name or "",
            "code": section.reference or "",
            "type_name": labels.get(section.type_section, section.type_section or ""),
            "niveau": levels.get(section.type_section, 0),
            "member_count": section.member_count or 0,
        }

    @http.route("/kiiraaye/get_section_org_chart", type="jsonrpc", auth="user")
    def get_section_org_chart(self, section_id, new_parent_id=None, **kw):
        section = self._get_section(section_id)
        if not section:
            return {
                "self": None,
                "managers": [],
                "children": [],
                "managers_more": False,
            }

        context = kw.get("context") or {}
        max_level = int(context.get("max_level") or self._managers_level)

        parent = (
            self._get_section(new_parent_id)
            if new_parent_id is not None
            else section._section_hierarchy_parent()
        )

        ancestors = []
        while (
            parent
            and parent != section
            and parent not in ancestors
            and len(ancestors) < max_level
        ):
            ancestors.append(parent)
            parent = parent._section_hierarchy_parent()

        children = section._section_hierarchy_children()

        return {
            "self": self._prepare_section_data(section),
            "managers": [
                self._prepare_section_data(record)
                for record in reversed(ancestors)
            ],
            "managers_more": bool(parent),
            "children": [
                self._prepare_section_data(record)
                for record in children
            ],
        }
