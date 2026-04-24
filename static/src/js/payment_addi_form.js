/**
 * payment_addi_form.js — Patch de PaymentForm para Addi en checkout
 *
 * Detecta provider_code === 'addi' y redirige a addi_redirect_url
 * sin esperar formulario HTML.
 */
(function () {
    "use strict";

    var PATCHED = false;

    function doPatch() {
        if (PATCHED) return;
        if (!window.publicWidget ||
            !window.publicWidget.registry ||
            !window.publicWidget.registry.PaymentForm) {
            return false;
        }

        var Proto = window.publicWidget.registry.PaymentForm.prototype;
        var original = Proto._processRedirectFlow;

        if (!original) {
            console.warn("[Addi] _processRedirectFlow no encontrado");
            return false;
        }

        var originalMethod = original.bind(Proto);

        Proto._processRedirectFlow = function (
            providerCode,
            paymentOptionId,
            paymentMethodCode,
            processingValues
        ) {
            if (providerCode === "addi") {
                var url = processingValues.addi_redirect_url;
                if (url) {
                    console.log("[Addi] Redirect a:", url);
                    window.location.href = url;
                    return;
                } else {
                    console.error("[Addi] Sin redirect_url en:", processingValues);
                    this._displayErrorDialog(
                        "Error",
                        "No se pudo obtener URL de Addi"
                    );
                    this._enableButton();
                    return;
                }
            }
            return originalMethod.call(
                this, providerCode, paymentOptionId, paymentMethodCode, processingValues
            );
        };

        PATCHED = true;
        console.log("[Addi] PaymentForm patcheado");
        return true;
    }

    function init() {
        var tries = 0;
        var interval = setInterval(function () {
            tries++;
            if (doPatch() || tries > 30) {
                clearInterval(interval);
            }
        }, 100);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();