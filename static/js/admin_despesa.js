/* static/js/admin_despesa.js */
document.addEventListener('DOMContentLoaded', function() {
    const $ = django.jQuery;

    // Classes CSS dos campos
    const camposCaixinha = ['.field-comprovante'];
    const camposSolicitacao = [
        '.field-inicio_cobertura', '.field-fim_cobertura',
        '.field-tomador', '.field-filial',
        '.field-motivo_ausencia', '.field-colaborador_faltou',
        '.field-nome_cobriu', '.field-forma_pagamento',
        '.field-dados_bancarios_pagto'
    ];

    function toggleFields() {
        // 1. Tenta pegar o tipo da URL (?tipo=SOLICITACAO)
        const urlParams = new URLSearchParams(window.location.search);
        let selectedType = urlParams.get('tipo');

        // 2. Se não tem na URL, tenta pegar da tela (caso esteja editando um existente)
        // O Django readonly renderiza um texto dentro de div.readonly
        if (!selectedType) {
            const fieldText = $('.field-tipo_lancamento .readonly').text().trim();
            if (fieldText.includes('Caixinha') || fieldText === 'CAIXINHA') {
                selectedType = 'CAIXINHA';
            } else if (fieldText.includes('Solicitação') || fieldText === 'SOLICITACAO') {
                selectedType = 'SOLICITACAO';
            }
        }

        // 3. Aplica a visibilidade
        if (selectedType === 'SOLICITACAO') {
            console.log("Modo: Solicitação");
            camposSolicitacao.forEach(function(cls) { $(cls).show(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        } else if (selectedType === 'CAIXINHA') {
            console.log("Modo: Caixinha");
            camposCaixinha.forEach(function(cls) { $(cls).show(); });
            camposSolicitacao.forEach(function(cls) { $(cls).hide(); });
        } else {
            // Se falhar tudo (ex: rascunho sem tipo definido), esconde os específicos
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
            camposSolicitacao.forEach(function(cls) { $(cls).hide(); });
        }
    }

    // Roda ao carregar
    toggleFields();
});