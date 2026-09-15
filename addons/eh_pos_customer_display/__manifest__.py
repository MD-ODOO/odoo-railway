# Part of the ERP Heritage POS Displays suite.
{
    'post_init_hook': 'post_init_hook',
    'name': 'Customer Display Theme',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Free dark ERP Heritage theme for the Odoo Community checkout customer display: a premium dark, mint-accented skin scoped to the customer screen, cosmetic only.',
    'description': 'A cosmetic dark theme for the standard Odoo Community checkout customer display. It re-skins the existing customer screen in the ERP Heritage dark, mint-accented look and adds a quiet ERP Heritage signature. Scoped to the customer display only, so it changes nothing else. Pairs with the ERP Heritage Kitchen Display and Order Status Screen for one consistent front of house.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au',
    'license': 'OPL-1',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale.customer_display_assets': ['eh_pos_customer_display/static/src/customer_display_theme.scss'],
    },
    'installable': True,
    'application': False,
    'images': ['static/description/banner.gif'],
}
