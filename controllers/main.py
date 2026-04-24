# -*- coding: utf-8 -*-
"""
Controladores HTTP del módulo payment_addi
==========================================
Rutas expuestas:
  POST /payment/addi/create      → crea transacción y devuelve URL
  POST /payment/addi/webhook     → recibe notificaciones de Addi
  GET  /payment/addi/return      → landing tras volver de Addi
  GET  /payment/addi/availability → disponibilidad por monto
"""
import json
import logging

from odoo import http
from odoo.http import request

from ..services.addi_api import AddiApiService

_logger = logging.getLogger(__name__)


class AddiController(http.Controller):

    # ── 1. Crear transacción ──────────────────────────────────────────────────

    @http.route(
        '/payment/addi/create',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
        website=True,
    )
    def addi_create_transaction(self, **kwargs):
        """
        Recibe: { amount, currency_id, partner_id, sale_order_id, access_token }
        Devuelve: { redirect_url } o { error }
        """
        try:
            data = request.get_json_data()
            amount = float(data.get('amount', 0))
            currency_id = int(data.get('currency_id', 0))
            partner_id = int(data.get('partner_id', 0))
            reference = data.get('reference', '')
            sale_order_id = data.get('sale_order_id')

            # Obtener provider Addi activo
            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'addi'), ('state', 'in', ('enabled', 'test'))],
                limit=1,
            )
            if not provider:
                return {'error': 'El proveedor Addi no está habilitado.'}

            currency = request.env['res.currency'].sudo().browse(currency_id)
            partner = request.env['res.partner'].sudo().browse(partner_id)

            # Crear o recuperar transacción de pago
            tx_vals = {
                'amount': amount,
                'currency_id': currency.id,
                'partner_id': partner.id,
                'provider_id': provider.id,
                'reference': reference or request.env['payment.transaction']._compute_reference(
                    provider_code='addi'
                ),
                'operation': 'online_redirect',
            }
            if sale_order_id:
                tx_vals['sale_order_ids'] = [(4, int(sale_order_id))]

            tx = request.env['payment.transaction'].sudo().create(tx_vals)

            # Generar URL de Addi
            addi_url = provider._addi_make_payment_url(tx)

            _logger.info("Addi: tx %s → redirect %s", tx.reference, addi_url)
            return {'redirect_url': addi_url, 'tx_reference': tx.reference}

        except Exception as exc:
            _logger.exception("Addi create_transaction error: %s", exc)
            return {'error': str(exc)}

    # ── 2. Webhook ────────────────────────────────────────────────────────────

    @http.route(
        '/payment/addi/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def addi_webhook(self, **kwargs):
        """
        Recibe notificaciones POST de Addi.
        Regla de Addi: responder HTTP 200 con el MISMO body recibido.
        """
        try:
            raw_body = request.httprequest.get_data(as_text=True)
            _logger.info("Addi webhook raw body: %s", raw_body)

            notification_data = json.loads(raw_body) if raw_body else {}

            # Localizar y procesar la transacción
            tx_sudo = request.env['payment.transaction'].sudo()
            tx = tx_sudo._get_tx_from_notification_data('addi', notification_data)
            tx._process_notification_data(notification_data)

            _logger.info(
                "Addi webhook procesado: tx=%s estado=%s",
                tx.reference,
                tx.state,
            )

        except Exception as exc:
            _logger.exception("Addi webhook error (se responde 200 de todas formas): %s", exc)
            # Se responde 200 siempre para que Addi no reintente
            raw_body = request.httprequest.get_data(as_text=True) or '{}'

        # Addi requiere: HTTP 200 + mismo body
        return request.make_response(
            raw_body,
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Length', str(len(raw_body.encode('utf-8')))),
            ],
            status=200,
        )

    # ── 3. Return URL (después de Addi) ───────────────────────────────────────

    @http.route(
        '/payment/addi/return',
        type='http',
        auth='public',
        methods=['GET'],
        website=True,
    )
    def addi_return(self, **kwargs):
        """
        Addi redirige aquí tras completar el flujo.
        Parámetros posibles: status, orderId, reference
        """
        status = kwargs.get('status', '').lower()
        reference = kwargs.get('reference') or kwargs.get('orderId', '')

        _logger.info("Addi return: status=%s reference=%s", status, reference)

        if status == 'approved':
            return request.redirect('/shop/confirmation')
        else:
            # rejected, declined, abandoned, o cualquier otro
            if status:
                request.session['addi_payment_error'] = f"Pago no completado: {status}"
            return request.redirect('/shop/cart')

    # ── 4. Disponibilidad ─────────────────────────────────────────────────────

    @http.route(
        '/payment/addi/availability',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
        website=True,
    )
    def addi_availability(self, **kwargs):
        """
        Verifica si Addi está disponible para el monto enviado.
        Recibe: { amount }
        Devuelve: { available, min_amount, max_amount, is_active }
        """
        try:
            data = request.get_json_data()
            amount = float(data.get('amount', 0))

            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'addi'), ('state', 'in', ('enabled', 'test'))],
                limit=1,
            )
            if not provider:
                return {'available': False, 'error': 'Proveedor Addi no encontrado.'}

            service = AddiApiService(provider)
            result = service.check_availability(amount)
            return result

        except Exception as exc:
            _logger.exception("Addi availability error: %s", exc)
            return {'available': False, 'error': str(exc)}
