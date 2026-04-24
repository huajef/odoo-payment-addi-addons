(function () {
    "use strict";

    let PATCHED = false;

    function doPatch() {

        if (PATCHED) return true;

        console.log("🔥 ADDI PATCH INIT 🔥");

        if (!window.publicWidget ||
            !window.publicWidget.registry ||
            !window.publicWidget.registry.PaymentForm) {
            return false;
        }

        const PaymentForm = window.publicWidget.registry.PaymentForm.prototype;

        const originalProcess = PaymentForm._processRedirectFlow;

        if (!originalProcess) {
            console.warn("[Addi] _processRedirectFlow no encontrado");
            return false;
        }

        PaymentForm._processRedirectFlow = function (
            providerCode,
            paymentOptionId,
            paymentMethodCode,
            processingValues
        ) {

            console.log("🔥 ENTER ADDI FLOW");
            console.log("providerCode:", providerCode);
            console.log("processingValues:", processingValues);

            if (providerCode === "addi") {

                const url = processingValues?.addi_redirect_url;

                if (url) {
                    console.log("[Addi] Redirect:", url);
                    window.location.href = url;
                    return;
                }

                console.error("[Addi] No redirect URL:", processingValues);

                if (this._displayErrorDialog) {
                    this._displayErrorDialog(
                        "Error",
                        "No se pudo obtener URL de Addi"
                    );
                }

                if (this._enableButton) {
                    this._enableButton();
                }

                return;
            }

            return originalProcess.apply(this, arguments);
        };

        PATCHED = true;
        console.log("[Addi] PATCH aplicado correctamente");
        return true;
    }

    function init() {

    console.log("🔥 ADDI SCRIPT LOADED 2🔥");

    const interval = setInterval(() => {

        if (
            window.publicWidget &&
            window.publicWidget.registry &&
            window.publicWidget.registry.PaymentForm &&
            window.publicWidget.registry.PaymentForm.prototype._processRedirectFlow
        ) {
            clearInterval(interval);
            doPatch();
        }

    }, 200);
}

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
