// Usa DOM nativo para evitar conflito entre django.jQuery e jQuery do Jazzmin
(function () {
    function toggleContractFields() {
        var tipoEl = document.getElementById('id_tipo');
        if (!tipoEl) return;

        var isFixo = tipoEl.value === 'FIXO';

        ['id_dia_vencimento', 'id_valor_contrato'].forEach(function (fieldId) {
            var input = document.getElementById(fieldId);
            if (!input) return;
            var row = input.closest('.form-group');
            if (row) row.style.display = isFixo ? '' : 'none';
        });
    }

    function init() {
        var tipoEl = document.getElementById('id_tipo');
        if (!tipoEl) return;

        // Esconde campos na carga inicial
        toggleContractFields();

        // Evento nativo (funciona independente de jQuery / Select2)
        tipoEl.addEventListener('change', toggleContractFields);

        // Select2 cria um container separado — observa mudanças via MutationObserver
        // e escuta o evento customizado que o Select2 dispara no DOM
        tipoEl.addEventListener('select2:select', toggleContractFields);

        // Fallback: observa mudança de valor via polling leve (100ms)
        var lastValue = tipoEl.value;
        setInterval(function () {
            if (tipoEl.value !== lastValue) {
                lastValue = tipoEl.value;
                toggleContractFields();
            }
        }, 150);
    }

    // Aguarda DOM pronto + Select2 inicializar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            setTimeout(init, 600);
        });
    } else {
        setTimeout(init, 600);
    }
})();
