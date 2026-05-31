/* static/js/admin_despesa.js - VERSÃO BLINDADA */
document.addEventListener('DOMContentLoaded', function() {
    const $ = django.jQuery;

    // --- 1. DEFINIÇÃO DOS GRUPOS DE CAMPOS ---
    const camposCaixinha = ['.field-comprovante'];
    const camposGerais = [
        '.field-inicio_cobertura', '.field-fim_cobertura',
        '.field-tomador', '.field-filial',
        '.field-motivo_ausencia', '.field-colaborador_faltou',
        '.field-nome_cobriu', '.field-forma_pagamento',
        '.field-dados_bancarios_pagto'
    ];

    function toggleFields() {
        // --- 2. DETECÇÃO DO TIPO ATUAL (AGORA MAIS INTELIGENTE) ---
        let selectedType = null;

        // TENTATIVA 1: Pegar do campo oculto de segurança (Melhor método)
        // No Python definimos: self.fields['tipo_reserva'].initial = tipo_real
        const hiddenInput = $('#id_tipo_reserva').val();
        if (hiddenInput) {
            selectedType = hiddenInput.toUpperCase();
        }

        // TENTATIVA 2: Pegar da URL (Quando está criando novo)
        if (!selectedType) {
            const urlParams = new URLSearchParams(window.location.search);
            selectedType = urlParams.get('tipo');
        }

        // TENTATIVA 3: Pegar do select box (Se for editável)
        if (!selectedType) {
             selectedType = $('#id_tipo_lancamento').val();
        }

        // TENTATIVA 4: Ler o texto da tela (Último recurso, para campos Read-Only)
        if (!selectedType) {
            const fieldText = $('.field-tipo_lancamento .readonly').text().trim().toUpperCase();
            if (fieldText.includes('CAIXINHA')) selectedType = 'CAIXINHA';
            else if (fieldText.includes('SOLICITA')) selectedType = 'SOLICITACAO'; // Pega Solicitação e Solicitacao
            else if (fieldText.includes('EXTRA')) selectedType = 'EXTRA';
        }

        console.log("Admin JS - Tipo Final Detectado:", selectedType);

        // --- 3. LÓGICA DE EXIBIÇÃO ---
        if (selectedType === 'SOLICITACAO' || selectedType === 'EXTRA') {
            camposGerais.forEach(function(cls) { $(cls).show(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        }
        else if (selectedType === 'CAIXINHA') {
            camposCaixinha.forEach(function(cls) { $(cls).show(); });
            camposGerais.forEach(function(cls) { $(cls).hide(); });
        }
        else {
            // Se não achou nada, não esconde tudo. Mostra tudo por segurança ou mantém estado inicial.
            // Para evitar tela branca em caso de erro, vamos comentar o hide() total:
            // camposCaixinha.forEach(function(cls) { $(cls).hide(); });
            // camposGerais.forEach(function(cls) { $(cls).hide(); });
        }
    }

    // Executa ao carregar
    toggleFields();

    // Executa se mudar o select
    $('#id_tipo_lancamento').change(toggleFields);
});