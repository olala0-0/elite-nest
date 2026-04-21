from odoo import api, fields, models


class PropertyResidentialType(models.Model):
    _name = "property.residential.type"
    _description = "Property Residential Type"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "unique(name)",
        "Residential type name must be unique.",
    )

    @api.model
    def action_sync_residential_types(self):
        cr = self.env.cr
        source_table_names = [
            "property_detail",
            "property_project",
            "property_sub_project",
            "rent_contract",
            "sale_contract",
        ]
        direct_sync_table_names = [
            "property_detail",
            "property_project",
            "property_sub_project",
        ]
        residential_types = set()
        for table_name in source_table_names:
            cr.execute(
                f"""
                SELECT DISTINCT residential_type
                  FROM {table_name}
                 WHERE residential_type IS NOT NULL
                   AND residential_type != ''
                """
            )
            residential_types.update(row[0] for row in cr.fetchall() if row[0])

        if not residential_types:
            return

        existing_types = {
            rec.name: rec.id
            for rec in self.sudo().search([("name", "in", list(residential_types))])
        }
        missing_types = residential_types - set(existing_types)
        for name in missing_types:
            existing_types[name] = self.sudo().create({"name": name}).id

        for table_name in direct_sync_table_names:
            for name, record_id in existing_types.items():
                cr.execute(
                    f"""
                    UPDATE {table_name}
                       SET residential_type_id = %s
                     WHERE residential_type_id IS NULL
                       AND residential_type = %s
                    """,
                    [record_id, name],
                )

        cr.execute(
            """
            UPDATE rent_contract rc
               SET residential_type_id = pd.residential_type_id,
                   type = prt.name
              FROM property_detail pd
         LEFT JOIN property_residential_type prt
                ON prt.id = pd.residential_type_id
             WHERE rc.property_id = pd.id
            """
        )
        cr.execute(
            """
            UPDATE sale_contract sc
               SET residential_type_id = pd.residential_type_id
              FROM property_detail pd
             WHERE sc.property_id = pd.id
            """
        )
