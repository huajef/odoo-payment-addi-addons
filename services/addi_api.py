# -*- coding: utf-8 -*-
"""
AddiApiService
==============
Encapsula toda la comunicación con las APIs de Addi:
  - OAuth2 (client_credentials)  → token JWT
  - Channels API                 → disponibilidad del aliado
  - Transactions API             → creación de transacción BNPL
"""
import logging

import requests

_logger = logging.getLogger(__name__)

# Timeout en segundos para todas las llamadas HTTP
_HTTP_TIMEOUT = 15


class AddiApiService:
    """Servicio stateless para interactuar con las APIs de Addi."""

    def __init__(self, provider):
        """
        :param provider: record de payment.provider con code=='addi'
        """
        self._client_id = provider.addi_client_id
        self._client_secret = provider.addi_client_secret
        self._ally_slug = provider.addi_ally_slug
        self._auth_url = (provider.addi_auth_url or '').rstrip('/')
        self._api_url = (provider.addi_api_url or '').rstrip('/')
        self._channels_url = (provider.addi_channels_url or '').rstrip('/')

    # ── OAuth2 ────────────────────────────────────────────────────────────────

    def _get_access_token(self):
        """Obtiene un token JWT fresco (client_credentials).
        Se solicita uno nuevo por transacción, sin caché."""
        url = self._auth_url
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
        }
        try:
            resp = requests.post(
                url,
                data=payload,
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            _logger.error("Addi auth HTTP error: %s – %s", exc, exc.response.text)
            raise
        except requests.exceptions.RequestException as exc:
            _logger.error("Addi auth connection error: %s", exc)
            raise

        data = resp.json()
        token = data.get('access_token')
        if not token:
            raise ValueError(f"Addi no retornó access_token. Respuesta: {data}")

        _logger.debug("Addi: token obtenido correctamente.")
        return token

    def _auth_headers(self):
        token = self._get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    # ── Disponibilidad ────────────────────────────────────────────────────────

    def check_availability(self, amount: float) -> dict:
        """
        Consulta si Addi está disponible para el monto dado.

        Retorna dict con:
          - available (bool)
          - min_amount (float)
          - max_amount (float)
          - is_active (bool)
          - raw (dict original de la respuesta)
        """
        url = f"{self._channels_url}/allies/{self._ally_slug}/config"
        params = {'requestedamount': amount}

        try:
            resp = requests.get(url, params=params, timeout=_HTTP_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            _logger.warning("Addi availability HTTP error: %s", exc)
            return {'available': False, 'raw': {}}
        except requests.exceptions.RequestException as exc:
            _logger.warning("Addi availability connection error: %s", exc)
            return {'available': False, 'raw': {}}

        data = resp.json()
        _logger.debug("Addi availability response: %s", data)

        min_amount = float(data.get('minAmount', 0))
        max_amount = float(data.get('maxAmount', 0))
        is_active = bool(data.get('isActiveAlly', False))
        available = is_active and (min_amount <= amount <= max_amount)

        return {
            'available': available,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'is_active': is_active,
            'raw': data,
        }

    # ── Creación de transacción ───────────────────────────────────────────────

    def create_transaction(self, payload: dict) -> str:
        """
        Crea una transacción en Addi y retorna la URL de redirección.

        Addi responde con HTTP 302 y el header 'Location' contiene
        la URL donde el cliente debe completar el pago.
        Se desactiva el seguimiento automático de redirecciones para
        capturar ese header antes de que requests lo siga.

        :param payload: dict con la orden (orderId, totalAmount, client, etc.)
        :returns: URL de redirección a Addi
        :raises: requests.HTTPError si la respuesta no es 3xx
        """
        # url = f"{self._api_url}/transactions"
        url = f"{self._api_url}/online-applications"

        headers = self._auth_headers()

        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=_HTTP_TIMEOUT,
                allow_redirects=False,   # ← CRÍTICO: capturar Location sin seguirlo
            )
        except requests.exceptions.RequestException as exc:
            _logger.error("Addi create_transaction connection error: %s", exc)
            raise

        _logger.info(
            "Addi create_transaction status=%s headers=%s",
            resp.status_code,
            dict(resp.headers),
        )

        # Addi responde 302 con Location o 201/200 con URL en body
        if resp.status_code in (301, 302, 303, 307, 308):
            redirect_url = resp.headers.get('Location')
            if not redirect_url:
                raise ValueError("Addi respondió con redirect pero sin header Location.")
            _logger.info("Addi redirect URL: %s", redirect_url)
            return redirect_url

        if resp.status_code in (200, 201):
            data = resp.json()
            redirect_url = data.get('redirectUrl') or data.get('url') or data.get('checkoutUrl')
            if not redirect_url:
                raise ValueError(f"Addi respondió 2xx pero sin URL. Body: {data}")
            _logger.info("Addi redirect URL (body): %s", redirect_url)
            return redirect_url

        # Cualquier otro código es un error
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.error(
                "Addi create_transaction error %s: %s",
                resp.status_code,
                resp.text,
            )
            raise

        raise ValueError(f"Addi: respuesta inesperada {resp.status_code}: {resp.text}")
