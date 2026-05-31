/* static/js/admin_despesa.js - VERSÃO UNIFICADA E BLINDADA */
(function ($) {
    'use strict';

    // ─── 1. LÓGICA DE EXIBIÇÃO POR TIPO DE LANÇAMENTO ───────────────
    const camposCaixinha = ['.field-comprovante'];
    const camposGerais = [
        '.field-inicio_cobertura', '.field-fim_cobertura',
        '.field-tomador', '.field-filial',
        '.field-motivo_ausencia', '.field-colaborador_faltou',
        '.field-nome_cobriu', '.field-forma_pagamento',
        '.field-dados_bancarios_pagto'
    ];

    function toggleFields() {
        let selectedType = null;

        // TENTATIVA 1: Pegar do campo oculto de segurança
        const hiddenInput = $('#id_tipo_reserva').val();
        if (hiddenInput) {
            selectedType = hiddenInput.toUpperCase();
        }

        // TENTATIVA 2: Pegar da URL (quando está criando novo)
        if (!selectedType) {
            const urlParams = new URLSearchParams(window.location.search);
            selectedType = urlParams.get('tipo');
        }

        // TENTATIVA 3: Pegar do select box (se for editável)
        if (!selectedType) {
             selectedType = $('#id_tipo_lancamento').val();
        }

        // TENTATIVA 4: Ler o texto da tela (Último recurso, para campos Read-Only)
        if (!selectedType) {
            const fieldText = $('.field-tipo_lancamento .readonly').text().trim().toUpperCase();
            if (fieldText.includes('CAIXINHA')) selectedType = 'CAIXINHA';
            else if (fieldText.includes('SOLICITA')) selectedType = 'SOLICITACAO';
            else if (fieldText.includes('EXTRA')) selectedType = 'EXTRA';
        }

        // Aplica as regras de visibilidade
        if (selectedType === 'SOLICITACAO' || selectedType === 'EXTRA') {
            camposGerais.forEach(function(cls) { $(cls).show(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        }
        else if (selectedType === 'CAIXINHA') {
            camposCaixinha.forEach(function(cls) { $(cls).show(); });
            camposGerais.forEach(function(cls) { $(cls).hide(); });
        }
    }


    // ─── 2. LÓGICA DO MOTIVO DE CANCELAMENTO (STATUS) ───────────────
    function toggleMotivoCancelamento() {
        var $statusSelect = $('#id_status');
        if (!$statusSelect.length) return;

        var $motivoRow = $('.field-motivo_cancelamento');
        if (!$motivoRow.length) return;

        var statusAtual = $statusSelect.val();
        var ehCancelado = statusAtual && statusAtual.indexOf('CANCELADO') !== -1;

        if (ehCancelado) {
            $motivoRow.show();
        } else {
            $motivoRow.hide();
            // Limpa o campo ao esconder para não enviar valor residual pro banco
            $motivoRow.find('textarea, input').val('');
        }
    }


    // ─── 3. INICIALIZAÇÃO E EVENTOS DE TELA ─────────────────────────
    $(document).ready(function () {
        // Roda as duas funções na carga inicial da tela
        toggleFields();
        toggleMotivoCancelamento();

        // Reage instantaneamente a mudanças no Tipo de Lançamento
        $(document).on('change', '#id_tipo_lancamento', function () {
            toggleFields();
        });

        // Reage instantaneamente a mudanças no Status
        $(document).on('change', '#id_status', function () {
            toggleMotivoCancelamento();
        });
    });

}(django.jQuery));