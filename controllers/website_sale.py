# -*- coding: utf-8 -*-
import logging

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _inject_addi_context(response, product=None):
    """Inyecta variables de Addi en el contexto QWeb."""
    if not hasattr(response, 'qcontext'):
        _logger.warning("ADDI: Response no tiene qcontext")
        return
    
    try:
        # Buscar provider Addi - sin filtro de estado para debug
        providers = request.env['payment.provider'].sudo().search([('code', '=', 'addi')])
        _logger.info("ADDI: Providers encontrados: %s", providers.mapped('name'))
        
        addi_provider = providers[:1] if providers else None
        _logger.info("ADDI: Provider: %s, state: %s", 
                   addi_provider.name if addi_provider else None,
                   addi_provider.state if addi_provider else 'N/A')
        
        response.qcontext['addi_provider'] = addi_provider

        # Currency
        cop_currency = request.env['res.currency'].sudo().search(
            [('name', '=', 'COP')], limit=1
        ) or request.env['res.currency'].sudo().search([], limit=1)
        currency_id = cop_currency.id if cop_currency else 1
        response.qcontext['addi_currency_id'] = currency_id

        # Amount
        sale_order = request.website.sale_get_order()
        amount = 0
        if sale_order and sale_order.amount_total > 0:
            amount = sale_order.amount_total
        elif product:
            combination = product._get_combination_info()
            amount = combination.get('price', 0)
        response.qcontext['addi_amount'] = amount or 0
        _logger.info("ADDI: Amount: %s", amount)

        # Partner
        partner = request.env.user.partner_id
        response.qcontext['addi_partner_id'] = partner.id if partner else 0

    except Exception as exc:
        _logger.warning("ADDI: Error: %s", exc)
        response.qcontext['addi_provider'] = None
        response.qcontext['addi_currency_id'] = 1
        response.qcontext['addi_partner_id'] = 0
        response.qcontext['addi_amount'] = 0


class WebsiteSaleAddi(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        response = super().product(product, category=category, search=search, **kwargs)
        _logger.info("ADDI: Product page: %s", product.id)
        _inject_addi_context(response, product=product)
        return response

    @http.route()
    def payment(self, **kwargs):
        response = super().payment(**kwargs)
        _logger.info("ADDI: Payment page")
        _inject_addi_context(response)
        return response
