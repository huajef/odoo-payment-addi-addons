(function () {
    "use strict";

    console.log("🔥 ADDI DEBUG - Iniciando script de debugG 🔥");

    // ==========================================
    // DEBUG 1: Verificar estado del template QWeb
    // ==========================================
    function debugTemplateState() {
        console.log("=== ADDI DEBUG: Estado del Template ===");
        
        // Ver si existe el botón
        const btn = document.getElementById('addi_pay_button');
        console.log("🔥 ADDI DEBUG - Botón #addi_pay_button existe:", !!btn);
        if (btn) {
            console.log("🔥 ADDI DEBUG - Botón visible:", btn.offsetParent !== null);
            console.log("🔥 ADDI DEBUG - Botón display:", window.getComputedStyle(btn).display);
            console.log("🔥 ADDI DEBUG - Botón atributos:", {
                'data-amount': btn.getAttribute('data-amount'),
                'data-currency-id': btn.getAttribute('data-currency-id'),
                'data-partner-id': btn.getAttribute('data-partner-id'),
                'data-addi-pay': btn.getAttribute('data-addi-pay'),
                'class': btn.className,
            });
            console.log("🔥 ADDI DEBUG - Botón dataset:", btn.dataset);
        }

        // Ver contenedores padres
        const container = document.querySelector('.addi-pay-container');
        console.log("🔥 ADDI DEBUG - Contenedor .addi-pay-container existe:", !!container);
        if (container) {
            console.log("🔥 ADDI DEBUG - Contenedor visible:", container.offsetParent !== null);
            console.log("🔥 ADDI DEBUG - Contenedor display:", window.getComputedStyle(container).display);
        }

        // Ver widget de Addi
        const widget = document.querySelector('.addi-widget-container');
        console.log("🔥 ADDI DEBUG - Widget container existe:", !!widget);

        // Verificar estructura common de Odoo 18
        const productDetails = document.getElementById('product_details');
        console.log("🔥 ADDI DEBUG - #product_details existe:", !!productDetails);

        // Buscar cualquier contenedor de producto
        const allDivs = document.querySelectorAll('div[class*="product"]');
        console.log("🔥 ADDI DEBUG - Divs con 'product' en clase:", allDivs.length);

        // Buscar por todas las clases relevantes
        const priceContainers = document.querySelectorAll('[id*="price"], [class*="price"]');
        console.log("🔥 ADDI DEBUG - Elementsos con 'price':", priceContainers.length);
    }

    // ==========================================
    // DEBUG 2: Verificar provider desde el DOM
    // ==========================================
    function debugProviderData() {
        console.log("=== ADDI DEBUG: Datos del Provider ===");
        
        // Buscar any elemento que contenga datos del provider
        const bodyAttrs = document.body.dataset;
        console.log("🔥 ADDI DEBUG - body.dataset:", bodyAttrs);

        // Buscar en window
        console.log("🔥 ADDI DEBUG - window.__debug_info:", window.__debug_info);
        
        // Buscar en odoo
        if (window.odoo) {
            console.log("🔥 ADDI DEBUG - odoo:", Object.keys(window.odoo));
        }
    }

    // ==========================================
    // DEBUG 3: Inicializar botón
    // ==========================================
    function initAddiButton() {
        const button = document.getElementById('addi_pay_button');
        if (!button) {
            console.log("🔥 ADDI DEBUG - Botón no encontrado en DOM");
            return false;
        }

        console.log("🔥 ADDI DEBUG - ¡Botón encontrado!");

        // Leer atributos
        const dataAmount = button.getAttribute('data-amount');
        const dataCurrencyId = button.getAttribute('data-currency-id');
        const dataPartnerId = button.getAttribute('data-partner-id');
        
        console.log("🔥 ADDI DEBUG - Atributos originales:", {
            'data-amount': dataAmount,
            'data-currency-id': dataCurrencyId,
            'data-partner-id': dataPartnerId
        });

        // Si ya tiene evento, no duplicar
        if (button.hasAttribute('data-addi-listener')) {
            console.log("🔥 ADDI DEBUG - Botón ya tiene listener");
            return true;
        }

        button.addEventListener('click', async function (e) {
            e.preventDefault();
            e.stopPropagation();

            console.log("🔥 ADDI DEBUG - ===== CLICK =====");

            // Obtener amount desde atributos
            let amount = 0;
            let currencyId = 1;
            let partnerId = 0;

            // intento 1: desde dataset
            console.log("🔥 ADDI DEBUG - Intentando dataset...");
            if (button.dataset.amount) {
                amount = parseFloat(button.dataset.amount);
                console.log("🔥 ADDI DEBUG - Amount desde dataset:", amount);
            }

            if (!amount || isNaN(amount)) {
                console.log("🔥 ADDI DEBUG - Fallback: buscando .oe_currency_value...");
                const priceEl = document.querySelector('.oe_currency_value');
                if (priceEl) {
                    const text = priceEl.textContent.replace(/[^0-9.,]/g, '').replace(',', '.');
                    amount = parseFloat(text);
                    console.log("🔥 ADDI DEBUG - Amount desde .oe_currency_value:", amount);
                }
            }

            if (!amount || isNaN(amount)) {
                console.log("🔥 ADDI DEBUG - Fallback: buscando #product_price...");
                const priceEl = document.getElementById('product_price');
                if (priceEl) {
                    const text = priceEl.textContent.replace(/[^0-9.,]/g, '').replace(',', '.');
                    amount = parseFloat(text);
                    console.log("🔥 ADDI DEBUG - Amount desde #product_price:", amount);
                }
            }

            if (!amount || isNaN(amount)) {
                console.log("🔥 ADDI DEBUG - Fallback: buscando todos los precios...");
                const priceEls = document.querySelectorAll('[class*="oe_currency_value"], [id*="price"]');
                for (let el of priceEls) {
                    const text = el.textContent.replace(/[^0-9.,]/g, '').replace(',', '.');
                    const parsed = parseFloat(text);
                    if (!isNaN(parsed) && parsed > 0) {
                        amount = parsed;
                        console.log("🔥 ADDI DEBUG - Amount desde " + el.className + ":", amount);
                        break;
                    }
                }
            }

            console.log("🔥 ADDI DEBUG - Amount FINAL:", amount);

            // Currency
            if (button.dataset.currencyId) {
                currencyId = parseInt(button.dataset.currencyId);
                console.log("🔥 ADDI DEBUG - Currency ID:", currencyId);
            } else {
                console.log("🔥 ADDI DEBUG - Sin currencyId, usando default 1");
            }

            // Partner
            if (button.dataset.partnerId) {
                partnerId = parseInt(button.dataset.partnerId);
                console.log("🔥 ADDI DEBUG - Partner ID:", partnerId);
            }

            if (!amount || isNaN(amount) || amount <= 0) {
                console.error("🔥 ADDI DEBUG ERROR: Amount inválido:", amount);
                alert("No se pudo obtener el monto. Revisa la consola para más detalles.");
                return;
            }

            // Desactivar botón
            const originalText = button.textContent;
            button.disabled = true;
            button.textContent = "Procesando...";
            console.log("🔥 ADDI DEBUG - Enviando al backend...");

            try {
                const response = await fetch('/payment/addi/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        amount: amount,
                        currency_id: currencyId,
                        partner_id: partnerId,
                        sale_order_id: null,
                    }),
                });

                const data = await response.json();
                console.log("🔥 ADDI DEBUG - Respuesta:", data);

                if (data.error) {
                    console.error("🔥 ADDI DEBUG ERROR:", data.error);
                    alert("Error: " + data.error);
                    button.disabled = false;
                    button.textContent = originalText;
                    return;
                }

                if (data.redirect_url) {
                    console.log("🔥 ADDI DEBUG - Redireccionando a:", data.redirect_url);
                    window.location.href = data.redirect_url;
                } else {
                    console.error("🔥 ADDI DEBUG - Sin redirect_url");
                    alert("Error: No se recibió URL");
                    button.disabled = false;
                    button.textContent = originalText;
                }
            } catch (error) {
                console.error("🔥 ADDI DEBUG EXCEPTION:", error);
                alert("Error: " + error.message);
                button.disabled = false;
                button.textContent = originalText;
            }
        });

        button.setAttribute('data-addi-listener', 'true');
        console.log("🔥 ADDI DEBUG - Listener agregado");
        return true;
    }

    // ==========================================
    // INIT: Ejecutar en carga
    // ==========================================
    function run() {
        console.log("🔥 ADDI DEBUG - run() ejecutándose...");
        
        // Estado del template
        debugTemplateState();
        
        // Datos del provider  
        debugProviderData();

        // Intentar inicializar botón
        let attempts = 0;
        const maxAttempts = 30;
        
        const interval = setInterval(() => {
            attempts++;
            const btn = document.getElementById('addi_pay_button');
            
            console.log("🔥 ADDI DEBUG - Intento", attempts, "de", maxAttempts, "- Botón existe:", !!btn);
            
            if (btn) {
                clearInterval(interval);
                initAddiButton();
            } else if (attempts >= maxAttempts) {
                clearInterval(interval);
                console.log("🔥 ADDI DEBUG - Dumping toda la página para debug:");
                console.log("🔥 ADDI DEBUG - Body innerHTML первые 2000 chars:", document.body.innerHTML.substring(0, 2000));
            }
        }, 500);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run);
    } else {
        run();
    }

})();