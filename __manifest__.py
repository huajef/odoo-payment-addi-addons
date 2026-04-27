# -*- coding: utf-8 -*-
{
    'name': 'Addi Payment Provider',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Addi BNPL payment provider for Colombia',
    'description': """
        Integración de Addi (Buy Now Pay Later Colombia) como método de pago
        en Odoo 18. Soporta flujo de redirección con webhook de confirmación.
        
        Configuración requerida:
        - addi_client_id: Client ID de OAuth2 (solicitar a soporte-aliados@addi.com)
        - addi_client_secret: Client Secret de OAuth2
        - addi_ally_slug: Slug único del comercio
    """,
    'author': 'Custom',
    'depends': ['payment', 'website_sale'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/product_template.xml',
        'views/payment_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_addi/static/src/js/addi_button.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
