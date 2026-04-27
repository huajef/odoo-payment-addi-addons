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
import base64
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

            _logger.info("🔥 ADDI CONTROLLER - Datos recibidos: amount=%s, currency_id=%s, partner_id=%s",
                         amount, currency_id, partner_id)

            # Obtener provider Addi activo
            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'addi'), ('state', 'in', ('enabled', 'test'))],
                limit=1,
            )

            _logger.info("🔥 ADDI CONTROLLER - Provider encontrado: %s", provider)

            if not provider:
                return {'error': 'El proveedor Addi no está habilitado.'}

            currency = request.env['res.currency'].sudo().browse(currency_id)
            partner = request.env['res.partner'].sudo().browse(partner_id)

            # 🔥 payment method seguro - Buscar método 'addi' primero
            payment_method = provider.payment_method_id
            _logger.info("🔥 ADDI CONTROLLER - Provider payment_method_id: %s", provider.payment_method_id)
            
            if not payment_method:
                payment_method = request.env['payment.method'].sudo().search([
                    ('name', 'ilike', 'addi')
                ], limit=1)
            
            if not payment_method:
                payment_method = request.env['payment.method'].sudo().search([
                    ('name', 'ilike', 'manual')
                ], limit=1)

            if not payment_method:
                _logger.error("🔥 NO PAYMENT METHOD FOUND")
                return {'error': 'No payment method disponible'}
            _logger.info("🔥 PAYMENT METHOD FINAL: %s", payment_method.id)




            # Crear transacción
            tx_vals = {
                'amount': amount,
                'currency_id': currency.id,
                'partner_id': partner.id,
                'provider_id': provider.id,
                'payment_method_id': payment_method.id,
                'reference': reference or request.env['payment.transaction']._compute_reference(
                    provider_code='addi'
                ),
                'operation': 'online_redirect',
            }

            _logger.info("🔥 ADDI DEBUG - TX VALS FINAL: %s", tx_vals)
            tx = request.env['payment.transaction'].sudo().create(tx_vals)
            _logger.info("🔥 ADDI DEBUG - TX CREADA: id=%s ref=%s amount=%s",
                tx.id, tx.reference, tx.amount)

            #borrar la linea siguinete:
            _logger.info("🔥 ADDI CONTROLLER - Tx vals: %s", tx_vals)

            # Generar URL Addi
            _logger.error("🔥 ADDI DEBUG - TX creada: %s", tx)
            _logger.error("🔥 ADDI DEBUG - TX amount: %s", tx.amount)
            _logger.error("🔥 ADDI DEBUG - TX partner: %s", tx.partner_id)

            addi_url = provider._addi_make_payment_url(tx)
            #linea fuera de codigo puede borrar (la siguiente)
            _logger.info("🔥 ADDI CONTROLLER - Redirect URL: %s", addi_url)

            _logger.info("🔥 ADDI DEBUG - RAW ADDI RESPONSE: %s", addi_url)
            _logger.info("🔥 ADDI DEBUG - TYPE: %s", type(addi_url))

            # segmento de codigo a elimeinar 
            """
            return {
                'redirect_url': addi_url,
                'tx_reference': tx.reference,
                'debug': str(addi_url),
            }
            """
            # Normalizar respuesta
            if isinstance(addi_url, dict):
                addi_url = (
                    addi_url.get("redirect_url")
                    or addi_url.get("url")
                    or addi_url.get("data", {}).get("redirect_url")
                    or addi_url.get("data", {}).get("url")
                )
            if not addi_url:
                _logger.error("🔥 ADDI CONTROLLER - addi_url está vacío!")
                return {'error': 'No se pudo generar URL de Addi. Verifica la configuración del provider.'}
            

            if isinstance(addi_url, dict):
                            addi_url = (
                                addi_url.get("redirect_url")
                                or addi_url.get("url")
                                or addi_url.get("data", {}).get("redirect_url")
                                or addi_url.get("data", {}).get("url")
            )


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
        Regla Addi: HTTP 200 + mismo body.
        Las credenciales Basic Auth deben configurarse en el provider.
        """
        try:
            # Verificar Basic Auth (opcional - si está configurado en provider)
            auth_header = request.httprequest.headers.get('Authorization', '')
            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'addi')], limit=1,
            )
            if provider and provider.addi_client_id and provider.addi_client_secret:
                expected_auth = base64.b64encode(
                    f"{provider.addi_client_id}:{provider.addi_client_secret}".encode()
                ).decode()
                if not auth_header or auth_header.replace('Basic ', '') != expected_auth:
                    _logger.warning("Addi webhook: autenticación fallida")
                    return request.make_response(
                        '{"error": "Unauthorized"}',
                        headers=[('Content-Type', 'application/json')],
                        status=401,
                    )

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
            _logger.exception("Addi webhook error: %s", exc)
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
