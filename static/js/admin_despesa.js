/* static/js/admin_despesa.js */
document.addEventListener('DOMContentLoaded', function() {
    const $ = django.jQuery;

    // --- 1. DEFINIÇÃO DOS GRUPOS DE CAMPOS ---

    // Campos exclusivos de Caixinha
    const camposCaixinha = ['.field-comprovante'];

    // Campos usados em Solicitação e EXTRA (Operacionais + Pagamento)
    const camposGerais = [
        '.field-inicio_cobertura', '.field-fim_cobertura',
        '.field-tomador', '.field-filial',
        '.field-motivo_ausencia', '.field-colaborador_faltou',
        '.field-nome_cobriu', '.field-forma_pagamento',
        '.field-dados_bancarios_pagto'
    ];

    function toggleFields() {
        // --- 2. DETECÇÃO DO TIPO ATUAL ---

        // Tenta pegar da URL (quando cria novo: ?tipo=EXTRA)
        const urlParams = new URLSearchParams(window.location.search);
        let selectedType = urlParams.get('tipo');

        // Se não tem na URL, tenta pegar da tela (Edição/Visualização)
        if (!selectedType) {
            // Tenta ler o texto do campo readonly (Ex: "Tipo: Extra")
            const fieldText = $('.field-tipo_lancamento .readonly').text().trim().toUpperCase();

            if (fieldText.includes('CAIXINHA')) {
                selectedType = 'CAIXINHA';
            } else if (fieldText.includes('SOLICITAÇÃO') || fieldText.includes('SOLICITACAO')) {
                selectedType = 'SOLICITACAO';
            } else if (fieldText.includes('EXTRA')) {
                selectedType = 'EXTRA'; // <--- AQUI ESTAVA FALTANDO ANTES
            } else {
                // Última tentativa: pega do input (caso seja editável)
                selectedType = $('#id_tipo_lancamento').val();
            }
        }

        console.log("Admin JS - Tipo detectado:", selectedType);

        // --- 3. LÓGICA DE EXIBIÇÃO ---

        if (selectedType === 'SOLICITACAO' || selectedType === 'EXTRA') {
            // EXTRA e SOLICITAÇÃO mostram os dados operacionais e de pagamento
            camposGerais.forEach(function(cls) { $(cls).show(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        }
        else if (selectedType === 'CAIXINHA') {
            // CAIXINHA mostra comprovante e esconde o resto
            camposCaixinha.forEach(function(cls) { $(cls).show(); });
            camposGerais.forEach(function(cls) { $(cls).hide(); });
        }
        else {
            // Se não identificou (ou vazio), esconde os específicos para limpar a tela
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
            camposGerais.forEach(function(cls) { $(cls).hide(); });
        }
    }

    // Executa ao carregar a página
    toggleFields();

    // Executa se o usuário mudar o tipo manualmente (se o campo estiver habilitado)
    $('#id_tipo_lancamento').change(toggleFields);
});