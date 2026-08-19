/* Navegação por Enter no cadastro de Colaboradores da Folha.
   Ao pressionar Enter no campo "Valor padrão", pula para o mesmo campo
   na linha de baixo — evita ficar rolando a tela com o mouse em folhas
   com muitos colaboradores. */
(function () {
  'use strict';

  function focarProximo(input) {
    // name segue o padrão "prefixo-N-valor_padrao" (formset do Django admin)
    var m = input.name.match(/^(.+)-(\d+)-valor_padrao$/);
    if (!m) return;
    var prefixo = m[1];
    var indiceAtual = parseInt(m[2], 10);
    var proximo = document.querySelector(
      'input[name="' + prefixo + '-' + (indiceAtual + 1) + '-valor_padrao"]'
    );
    if (proximo) {
      proximo.focus();
      proximo.select();
      proximo.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }

  function ligar() {
    document.querySelectorAll('input[name$="-valor_padrao"]').forEach(function (input) {
      if (input.dataset.enterNavLigado) return;
      input.dataset.enterNavLigado = '1';
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          focarProximo(input);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', ligar);

  // Django admin cria novas linhas dinamicamente (botão "Adicionar outro(a)")
  // — reobserva o container para ligar o Enter nas linhas recém-criadas.
  document.addEventListener('DOMContentLoaded', function () {
    var alvo = document.querySelector('#colaboradores-group, .inline-group');
    if (!alvo) return;
    var observer = new MutationObserver(ligar);
    observer.observe(alvo, { childList: true, subtree: true });
  });
})();
