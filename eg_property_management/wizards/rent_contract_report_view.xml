<odoo>
    <data>
        <record id="rent_contract_wizard_form_view" model="ir.ui.view">
            <field name="name">rent.contract.report.form</field>
            <field name="model">rent.contract.report</field>
            <field name="arch" type="xml">
                <form>
                    <group>
                        <field name="landlord_id" required="1"/>

                        <!--                        <field name="rent_contract_ids"/>-->
                    </group>
                    <footer>
                        <button name="action_rent_contract_report" class="oe_highlight" string="Print" type="object"/>
                    </footer>
                </form>
            </field>
        </record>

        <record id="action_rent_contract_report" model="ir.actions.act_window">
            <field name="name">Rent Contract Landlord Report</field>
            <field name="res_model">rent.contract.report</field>
            <field name="view_mode">form</field>
            <field name="target">new</field>
        </record>
        <menuitem id="rent_contract_report_menu" name="Report" parent="property_management_menu" sequence="110"/>
        <menuitem id="rent_contract_report_submenu" name="Landlord Report" parent="rent_contract_report_menu"
                  sequence="10" action="action_rent_contract_report"/>
    </data>
</odoo>