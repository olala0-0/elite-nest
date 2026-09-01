from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompanyOverviewDashboard(TransactionCase):

    def test_get_data_shape(self):
        data = self.env['codeerts.company_overview.dashboard'].get_data()
        self.assertIn('kpis', data)
        self.assertIn('charts', data)
        for k in data['kpis']:
            self.assertIn('domain', k)
        cur = self.env['codeerts.company_overview.dashboard'].get_currency()
        self.assertEqual(set(cur), {'symbol', 'position', 'decimals'})
