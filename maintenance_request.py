<odoo>
    <data>
        <record id="rent_contract_full_report_wizard_form_view" model="ir.ui.view">
            <field name="name">rent.contract.full.report.form</field>
            <field name="model">rent.contract.full.report</field>
            <field name="arch" type="xml">
                <form>
                    <!--                        <field name="landlord_id" required="1"/>-->

                    <field name="rent_contract_ids" required="1"/>
                    <footer>
                        <button name="action_rent_contract_full_report" class="oe_highlight" string="Print"
                                type="object"/>
                    </footer>
                </form>
            </field>
        </record>

        <record id="action_rent_contract_full_report" model="ir.actions.act_window">
            <field name="name">Rent Contract Report</field>
            <field name="res_model">rent.contract.full.report</field>
            <field name="view_mode">form</field>
            <field name="target">new</field>
        </record>

        <menuitem id="rent_contract_full_report_submenu" name="Report" parent="rent_contract_report_menu"
                  sequence="20" action="action_rent_contract_full_report"/>
    </data>
</odoo>