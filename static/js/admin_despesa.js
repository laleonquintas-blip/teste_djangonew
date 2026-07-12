/* static/js/admin_despesa.js - VERSÃO UNIFICADA E BLINDADA */
(function ($) {
    'use strict';

    // ─── 1. LÓGICA DE EXIBIÇÃO POR TIPO DE LANÇAMENTO ───────────────
    const camposCaixinha = ['.field-comprovante'];
    const camposGerais = [
        '.field-inicio_cobertura', '.field-fim_cobertura',
        '.field-tomador', '.field-filial',
        '.field-motivo_ausencia', '.field-colaborador_faltou',
    ];
    const camposSolicitacao = [
        '.field-nome_cobriu',
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
        if (selectedType === 'SOLICITACAO') {
            camposGerais.forEach(function(cls) { $(cls).show(); });
            camposSolicitacao.forEach(function(cls) { $(cls).show(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        }
        else if (selectedType === 'EXTRA') {
            camposGerais.forEach(function(cls) { $(cls).show(); });
            camposSolicitacao.forEach(function(cls) { $(cls).hide(); });
            camposCaixinha.forEach(function(cls) { $(cls).hide(); });
        }
        else if (selectedType === 'CAIXINHA') {
            camposCaixinha.forEach(function(cls) { $(cls).show(); });
            camposGerais.forEach(function(cls) { $(cls).hide(); });
            camposSolicitacao.forEach(function(cls) { $(cls).hide(); });
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
        // Cobre tanto o select nativo quanto o Select2 (usado pelo Jazzmin)
        $(document).on('change', '#id_status', function () {
            toggleMotivoCancelamento();
        });
        $(document).on('select2:select select2:unselect', function (e) {
            if ($(e.target).attr('id') === 'id_status') {
                toggleMotivoCancelamento();
            }
        });

        // ─── 4. COLABORADOR INFO: callback do popup ──────────────────────────
        // Atualiza o Select2 quando um novo ColaboradorInfo é criado no popup
        var _origDismiss = window.dismissAddRelatedObjectPopup;
        window.dismissAddRelatedObjectPopup = function (win, newId, newRepr) {
            if (win.name === 'add_colaboradorinfo') {
                var $select = $('#id_colaborador_info');
                if ($select.length) {
                    var option = new Option(newRepr, newId, true, true);
                    $select.append(option).trigger('change');
                    $.getJSON('/api/colaborador-info/', { id: newId }, function (data) {
                        if (data.dados) {
                            var $dados = $('#id_dados_bancarios_pagto');
                            if ($dados.length && !$dados.prop('readonly')) $dados.val(data.dados);
                        }
                    });
                }
                win.close();
                return;
            }
            if (_origDismiss) _origDismiss(win, newId, newRepr);
        };

        // ─── 4b. COLABORADOR INFO → auto-preenche nome_cobriu e dados_bancarios ──
        $(document).on('select2:select', '#id_colaborador_info', function (e) {
            var id = e.params.data.id;
            if (!id) return;
            $.getJSON('/api/colaborador-info/', { id: id }, function (data) {
                if (data.nome) {
                    var $nome = $('#id_nome_cobriu');
                    if ($nome.length && !$nome.prop('readonly')) {
                        $nome.val(data.nome);
                    }
                }
                if (data.dados) {
                    var $dados = $('#id_dados_bancarios_pagto');
                    if ($dados.length && !$dados.prop('readonly')) {
                        $dados.val(data.dados);
                    }
                }
            });
        });

        // ─── 5. VAGAS EM ABERTO → auto-preenche colaborador_faltou ────
        $(document).on('change select2:select select2:unselect', '#id_motivo_ausencia', function () {
            var $motivo = $('#id_motivo_ausencia');
            var vagasMotivoId = $motivo.data('vagas-motivo-id');
            var vagasColabId  = $motivo.data('vagas-colab-id');
            if (!vagasMotivoId || !vagasColabId) return;

            var selecionado = $motivo.val();
            if (String(selecionado) === String(vagasMotivoId)) {
                var $colab = $('#id_colaborador_faltou');
                $colab.val(vagasColabId).trigger('change');
            }
        });
        // ─── 6. FOLHA → auto-preenche e trava o campo valor ────────────────
        function preencherValorFolha() {
            // Busca o texto "Total: R$ X.XXX,XX" no folha_resumo_display
            var resumo = $('.field-folha_resumo_display').text();
            var match = resumo.match(/Total:\s*R\$\s*([\d.,]+)/);
            if (match) {
                var valorStr = match[1].replace(/\./g, '').replace(',', '.');
                var $valor = $('#id_valor');
                if ($valor.length && !$valor.prop('readonly')) {
                    $valor.val(parseFloat(valorStr).toFixed(2));
                    $valor.prop('readonly', true).css('background','#e9ecef');
                }
            }
        }

        // Tenta preencher ao carregar (quando já há folha selecionada)
        setTimeout(preencherValorFolha, 800);

        // Tenta preencher ao mudar a folha (via Select2 ou change nativo)
        $(document).on('select2:select select2:clear change', '#id_pagamento_folha', function () {
            setTimeout(preencherValorFolha, 600);
        });
    });

}(django.jQuery));