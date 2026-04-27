# -*- coding: utf-8 -*-
import logging
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services.addi_api import AddiApiService

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('addi', 'Addi')],
        ondelete={'addi': 'set default'},
    )

    # ── Addi-specific fields ──────────────────────────────────────────────────
    addi_client_id = fields.Char(
        string='Client ID',
        help='OAuth2 client_id proporcionado por Addi.',
        groups='base.group_system',
    )
    addi_client_secret = fields.Char(
        string='Client Secret',
        help='OAuth2 client_secret proporcionado por Addi.',
        groups='base.group_system',
    )
    addi_ally_slug = fields.Char(
        string='Ally Slug',
        help='Slug del aliado en Addi (ej: mi-tienda).',
    )
    addi_auth_url = fields.Char(
        string='Auth URL',
         defauult = 'https://auth.addi-staging.com/oauth/token',
        #default='https://auth.addi.com/oauth/token',
        help='Endpoint OAuth2 de Addi.',
    )
    addi_api_url = fields.Char(
        string='API URL',
        default='https://api.addi.com/v1',
        help='URL base de la API de Addi.',
    )
    addi_channels_url = fields.Char(
        string='Channels API URL',
        default='https://channels-public-api.addi.com',
        help='URL base de la API de disponibilidad de Addi.',
    )

    # ── Computed helpers ──────────────────────────────────────────────────────
    @api.depends('code')
    def _compute_view_configuration_fields(self):
        super()._compute_view_configuration_fields()

    def _get_supported_currencies(self):
        supported = super()._get_supported_currencies()
        if self.code == 'addi':
            supported = supported.filtered(lambda c: c.name == 'COP')
        return supported

    # ── Redirect form ─────────────────────────────────────────────────────────
    def _get_redirect_form_values(self, notification_data):
        """No se usa formulario HTML clásico: la redirección se hace
        desde el frontend vía JS. Se devuelve dict vacío."""
        self.ensure_one()
        if self.code != 'addi':
            return super()._get_redirect_form_values(notification_data)
        return {}

    # ── Transaction creation ──────────────────────────────────────────────────
    def _addi_make_payment_url(self, tx):
        """Llama a la API de Addi y retorna la URL de redirección."""
        self.ensure_one()
        
        _logger.info("🔥 ADDI PROVIDER - Iniciando _addi_make_payment_url")
        _logger.info("🔥 ADDI PROVIDER - addi_client_id: %s", self.addi_client_id)
        _logger.info("🔥 ADDI PROVIDER - addi_ally_slug: %s", self.addi_ally_slug)
        _logger.info("🔥 ADDI PROVIDER - addi_auth_url: %s", self.addi_auth_url)
        _logger.info("🔥 ADDI PROVIDER - addi_api_url: %s", self.addi_api_url)
        
        service = AddiApiService(self)

        # Datos de la orden de venta vinculada
        sale_order = tx.sale_order_ids[:1]
        partner = tx.partner_id

        base_url = self.get_base_url()
        callback_url = f"{base_url}/payment/addi/webhook"
        redirect_url = f"{base_url}/payment/addi/return"

        # Identificador único para esta transacción
        order_id = f"ODOO-{tx.id}-{uuid.uuid4().hex[:8].upper()}"

        payload = {
            "orderId": order_id,
            #"totalAmount": float(tx.amount),
            "totalAmount": str(float(tx.amount)),
            "currency": tx.currency_id.name,
            #"callbackUrl": callback_url,
            #"redirectionUrl": redirect_url,
            "metadata": {
                "odoo_tx_reference": tx.reference,
                "odoo_tx_id": tx.id,
            },

            "allyUrlRedirection": {
                "callbackUrl": callback_url,
                "redirectionUrl": redirect_url,
            },
            "client": {
                "firstName": partner.name.split()[0] if partner.name else "Cliente",
                "lastName": " ".join(partner.name.split()[1:]) if partner.name and len(partner.name.split()) > 1 else ".",
                "email": partner.email or "",
                "cellphone": (partner.phone or partner.mobile or "").replace(" ", ""),
                "idType": "CC",
                "idNumber": partner.vat or "0000000000",
            },
            "shippingAddress": {
                "lineOne": partner.street or "N/A",
                "city": partner.city or "Bogotá",
                "country": "CO"
            },
        }

        if sale_order:
            items = []
            for line in sale_order.order_line:
                items.append({
                    "sku": line.product_id.default_code or str(line.product_id.id),
                    "name": line.product_id.name,
                    "quantity": int(line.product_uom_qty),
                    "unitPrice": float(line.price_unit),
                    "totalPrice": float(line.price_subtotal),
                })
            payload["items"] = items

        addi_url = service.create_transaction(payload)
        return addi_url


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'addi':
            return res

        addi_url = self.provider_id._addi_make_payment_url(self)
        res.update({'addi_redirect_url': addi_url})
        return res

    # ── Notification handling ─────────────────────────────────────────────────
    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'addi':
            return

        status = (notification_data.get('status') or '').lower()
        _logger.info("Addi webhook status=%s tx=%s", status, self.reference)

        if status == 'approved':
            self._set_done()
        elif status in ('rejected', 'declined'):
            self._set_error(f"Addi rechazó el pago: {status}")
        elif status == 'abandoned':
            self._set_canceled("El cliente abandonó el proceso en Addi.")
        else:
            _logger.warning("Addi: estado desconocido '%s' para tx %s", status, self.reference)

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        if provider_code != 'addi':
            return super()._get_tx_from_notification_data(provider_code, notification_data)

        # Addi envía el reference en metadata o en orderId
        reference = (
            notification_data.get('metadata', {}).get('odoo_tx_reference')
            or notification_data.get('orderId', '')
        )
        tx = self.search([
            ('reference', '=', reference),
            ('provider_code', '=', 'addi'),
        ], limit=1)
        if not tx:
            raise ValidationError(
                _("No se encontró transacción Addi con referencia: %s", reference)
            )
        return tx
