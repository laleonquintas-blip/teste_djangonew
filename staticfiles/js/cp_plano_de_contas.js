function cpPlanoInit() {
  var $ = window.$ || window.jQuery || django.jQuery;
  if (!$) { console.error('[cp_plano] jQuery nao encontrado'); return; }

  var $forn = $('#id_fornecedor');
  if (!$forn.length) { console.error('[cp_plano] #id_fornecedor nao encontrado'); return; }

  console.log('[cp_plano] iniciado, fornecedor val=' + $forn.val());

  function preencherPlano(fornecedorId) {
    if (!fornecedorId) return;
    console.log('[cp_plano] buscando id=' + fornecedorId);
    django.jQuery.getJSON('/api/fornecedor-info/', { id: fornecedorId }, function (data) {
      console.log('[cp_plano] resposta:', data);
      var $plano = $('#id_plano_de_contas');
      if (!$plano.length) return;
      if (data.plano_de_contas_id) {
        $plano.val(String(data.plano_de_contas_id)).trigger('change');
        // Bloqueia edição manual: desativa o widget Select2 visualmente
        $plano.next('.select2-container').css({'pointer-events': 'none', 'opacity': '0.65'});
      }
    });
  }

  $forn.on('select2:select', function (e) {
    console.log('[cp_plano] select2:select', e.params.data.id);
    preencherPlano(e.params.data.id);
  });

  $forn.on('change', function () {
    console.log('[cp_plano] change', $(this).val());
    preencherPlano($(this).val());
  });
}

// Executa quando o DOM estiver pronto, independente do estado atual
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', cpPlanoInit);
} else {
  cpPlanoInit();
}
