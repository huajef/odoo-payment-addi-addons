/**
 * addi_widget.js — Odoo 18 compatible (vanilla JS, no OWL imports)
 *
 * Maneja el botón "Pagar con Addi" en la página de producto.
 * No usa @odoo-module ni imports de /web/core para evitar el error
 * "Unallowed to fetch files from addon" en Odoo 18.
 *
 * Flujo:
 *   1. Click en botón → POST JSON-RPC a /payment/addi/create
 *   2. Recibe redirect_url → window.location.href
 */

(function () {
    "use strict";

    /**
     * Llama a un endpoint JSON-RPC de Odoo (compatible con /web/dataset/call_kw y rutas type='json').
     */
    async function jsonRpc(url, params) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                id: Math.floor(Math.random() * 1e9),
                params: params,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error.data?.message || data.error.message || "RPC Error");
        }

        return data.result;
    }

    /**
     * Muestra error inline junto al botón.
     */
    function showError(btn, message) {
        let errEl = btn.parentElement.querySelector(".addi-error-msg");
        if (!errEl) {
            errEl = document.createElement("p");
            errEl.className = "addi-error-msg";
            errEl.style.cssText = "color:#dc3545;font-size:0.85rem;margin-top:6px;";
            btn.parentElement.appendChild(errEl);
        }
        errEl.textContent = message;
    }

    function clearError(btn) {
        const errEl = btn.parentElement && btn.parentElement.querySelector(".addi-error-msg");
        if (errEl) errEl.remove();
    }

    /**
     * Lee el partner_id del contexto de sesión de Odoo 18.
     * Odoo 18 lo expone en odoo.__session_info__ o en el meta tag.
     */
    function getPartnerId() {
        try {
            if (window.__odoo_session_info__) {
                return window.__odoo_session_info__.partner_id || 0;
            }
            // fallback: leer del elemento oculto que website_sale inyecta
            const el = document.querySelector("[data-partner-id]");
            if (el) return parseInt(el.dataset.partnerId, 10) || 0;
        } catch (_) {}
        return 0;
    }

    /**
     * Obtiene el sale_order_id activo del carrito.
     */
    async function getSaleOrderId() {
        try {
            const result = await jsonRpc("/web/dataset/call_kw", {
                model: "sale.order",
                method: "search_read",
                args: [[["website_id", "!=", false], ["state", "=", "draft"]]],
                kwargs: {
                    fields: ["id"],
                    limit: 1,
                    order: "id desc",
                    context: {},
                },
            });
            return result && result.length ? result[0].id : null;
        } catch (_) {
            return null;
        }
    }

    /**
     * Handler del click en el botón Addi.
     */
    async function handleAddiPay(event) {
        const btn = event.currentTarget;
        clearError(btn);

        const amount = parseFloat(btn.dataset.amount || "0");
        const currencyId = parseInt(btn.dataset.currencyId || "0", 10);

        if (!amount || amount <= 0) {
            showError(btn, "Monto inválido para procesar con Addi.");
            return;
        }

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = "Procesando…";

        try {
            const partnerId = getPartnerId();
            const saleOrderId = await getSaleOrderId();

            const result = await jsonRpc("/payment/addi/create", {
                amount: amount,
                currency_id: currencyId,
                partner_id: partnerId,
                sale_order_id: saleOrderId,
            });

            if (!result || result.error) {
                showError(btn, "Error Addi: " + (result ? result.error : "sin respuesta"));
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            const redirectUrl = result.redirect_url;
            if (!redirectUrl) {
                showError(btn, "No se recibió URL de Addi. Intenta de nuevo.");
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            // Redirección manual — no automática
            window.location.href = redirectUrl;

        } catch (err) {
            console.error("[Addi] Error:", err);
            showError(btn, "Error de conexión con Addi. Intenta nuevamente.");
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    /**
     * Inicializa los botones Addi cuando el DOM esté listo.
     */
    function init() {
        const buttons = document.querySelectorAll("[data-addi-pay='1']");
        if (!buttons.length) return;

        buttons.forEach(function (btn) {
            btn.addEventListener("click", handleAddiPay);
        });

        console.log("[Addi] " + buttons.length + " botón(es) inicializado(s).");
    }

    // Compatible con Odoo 18: el script se carga diferido, el DOM ya está listo.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
