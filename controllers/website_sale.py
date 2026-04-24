# -*- coding: utf-8 -*-
"""
controllers/website_sale.py
============================
Hereda el controlador de website_sale para inyectar la variable
`addi_provider` en el contexto del template de producto.
Así el QWeb puede hacer t-if="addi_provider" sin errores.
"""
import logging

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteSaleAddi(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        """Sobreescribe la vista de producto para añadir addi_provider."""
        response = super().product(product, category=category, search=search, **kwargs)

        # Si la respuesta es un QWebResponse, inyectamos la variable
        if hasattr(response, 'qcontext'):
            try:
                addi_provider = request.env['payment.provider'].sudo().search(
                    [('code', '=', 'addi'), ('state', 'in', ('enabled', 'test'))],
                    limit=1,
                )
                response.qcontext['addi_provider'] = addi_provider
            except Exception as exc:
                _logger.warning("Addi: no se pudo inyectar provider en producto: %s", exc)
                response.qcontext['addi_provider'] = False

        return response
