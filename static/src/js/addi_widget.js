/**
 * addi_widget.js — Odoo 18 compatible (versión estable)
 *
 * Flujo:
 * 1. Click botón Addi
 * 2. Calcula monto de forma segura
 * 3. POST a /payment/addi/create
 * 4. Recibe redirect_url
 * 5. Redirige a Addi
 */

(function () {
    "use strict";

    console.log("[Addi] script cargado");

    /**
     * Llamada backend Odoo
     */
    async function callAddiCreate(payload) {
        const response = await fetch("/payment/addi/create", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: payload,
                id: Date.now(),
            }),
        });

        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }

        const data = await response.json();

        // Odoo JSON-RPC devuelve en result
        return data.result;
    }

    function showError(btn, msg) {
        let el = btn.parentElement.querySelector(".addi-error-msg");
        if (!el) {
            el = document.createElement("div");
            el.className = "addi-error-msg";
            el.style.color = "red";
            el.style.marginTop = "6px";
            btn.parentElement.appendChild(el);
        }
        el.textContent = msg;
    }

    function clearError(btn) {
        const el = btn.parentElement.querySelector(".addi-error-msg");
        if (el) el.remove();
    }

    function getPartnerId() {
        try {
            return window.__odoo_session_info__?.partner_id || 0;
        } catch (e) {
            return 0;
        }
    }

    /**
     * 🔥 FIX PRINCIPAL: obtener monto de forma robusta
     */
    function getCheckoutAmount(btn) {
        // 1. Intentar dataset del botón (si existe)
        let amount = parseFloat(btn.dataset.amount || "0");

        if (amount > 0) return amount;

        // 2. Intentar DOM clásico Odoo
        const el = document.querySelector(".oe_cart_total .monetary_field");

        if (el) {
            amount = parseFloat(el.innerText.replace(/[^0-9.]/g, "")) || 0;
        }

        return amount;
    }

    /**
     * CLICK PRINCIPAL
     */
    async function handleAddiPay(event) {
        const btn = event.currentTarget;

        console.log("[Addi] click detectado");

        clearError(btn);

        const amount = getCheckoutAmount(btn);
        const currencyId = parseInt(btn.dataset.currencyId || "0", 10);

        console.log("[Addi] amount detectado:", amount);

        // 🔥 VALIDACIÓN CORRECTA
        if (!amount || amount <= 0) {
            showError(btn, "Monto inválido. Intenta recargar el carrito2.");
            return;
        }

        const originalText = btn.textContent;

        btn.disabled = true;
        btn.textContent = "Procesando...";

        try {
            const payload = {
                amount: amount,
                currency_id: currencyId,
                partner_id: getPartnerId(),
                sale_order_id: null,
            };

            console.log("[Addi] payload:", payload);

            const result = await callAddiCreate(payload);

            console.log("[Addi] respuesta backend:", result);

            if (!result || result.error) {
                throw new Error(result?.error || "Error desconocido");
            }

            const redirectUrl = result.redirect_url;

            if (!redirectUrl) {
                throw new Error("No se recibió redirect_url");
            }

            console.log("[Addi] redirigiendo a:", redirectUrl);

            window.location.href = redirectUrl;

        } catch (err) {
            console.error("[Addi] error:", err);

            showError(btn, "Error Addi: " + err.message);

            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    /**
     * INIT seguro (espera botón dinámico Odoo)
     */
    function init() {
        console.log("[Addi] init ejecutado");

        const interval = setInterval(() => {
            const btn = document.getElementById("addi_pay_button");

            if (btn) {
                console.log("[Addi] botón encontrado");

                btn.addEventListener("click", handleAddiPay);

                clearInterval(interval);
            }
        }, 200);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();