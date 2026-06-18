/* Widget seletor de múltiplos dias de cobertura */
(function () {
  'use strict';

  function pad(n) { return String(n).padStart(2, '0'); }

  // Formato de armazenamento: dd-mm-yyyy
  function strToDate(str) {
    var p = str.split('-');
    return new Date(parseInt(p[2]), parseInt(p[1]) - 1, parseInt(p[0]));
  }

  function dateToBr(d) {
    return pad(d.getDate()) + '-' + pad(d.getMonth() + 1) + '-' + d.getFullYear();
  }

  function ptBrDisplay(br) {
    // dd-mm-yyyy → dd/mm/yyyy
    return br.replace(/-/g, '/');
  }

  // Ordena datas no formato dd-mm-yyyy corretamente
  function sortBrDates(arr) {
    return arr.slice().sort(function (a, b) {
      return strToDate(a) - strToDate(b);
    });
  }

  var MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  var DIAS_SEQ = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];

  function buildWidget(textarea) {
    var wrapper = document.createElement('div');
    wrapper.className = 'dias-cob-wrapper';
    wrapper.style.cssText = 'border:1px solid #ced4da;border-radius:6px;padding:12px;background:#fff;max-width:380px;';

    // ── Cabeçalho com navegação de mês ──
    var nav = document.createElement('div');
    nav.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;';

    var btnPrev = document.createElement('button');
    btnPrev.type = 'button';
    btnPrev.innerHTML = '&#8249;';
    btnPrev.style.cssText = 'border:none;background:none;font-size:20px;cursor:pointer;padding:0 6px;color:#495057;';

    var lblMes = document.createElement('span');
    lblMes.style.cssText = 'font-weight:bold;font-size:14px;color:#343a40;';

    var btnNext = document.createElement('button');
    btnNext.type = 'button';
    btnNext.innerHTML = '&#8250;';
    btnNext.style.cssText = 'border:none;background:none;font-size:20px;cursor:pointer;padding:0 6px;color:#495057;';

    nav.appendChild(btnPrev);
    nav.appendChild(lblMes);
    nav.appendChild(btnNext);
    wrapper.appendChild(nav);

    // ── Grid do calendário ──
    var grid = document.createElement('div');
    grid.style.cssText = 'display:grid;grid-template-columns:repeat(7,1fr);gap:3px;';
    wrapper.appendChild(grid);

    // ── Dias selecionados ──
    var tagsWrap = document.createElement('div');
    tagsWrap.style.cssText = 'margin-top:10px;display:flex;flex-wrap:wrap;gap:5px;min-height:24px;';
    wrapper.appendChild(tagsWrap);

    // ── Legenda ──
    var leg = document.createElement('p');
    leg.textContent = 'Dias de cobertura!';
    leg.style.cssText = 'margin:6px 0 0;font-size:11px;color:#6c757d;';
    wrapper.appendChild(leg);

    textarea.style.display = 'none';
    textarea.parentNode.insertBefore(wrapper, textarea);

    var hoje = new Date();
    var viewAno = hoje.getFullYear();
    var viewMes = hoje.getMonth();
    var selected = new Set();

    // Carrega valores existentes
    if (textarea.value.trim()) {
      textarea.value.trim().split(',').forEach(function (s) {
        s = s.trim();
        if (s) selected.add(s);
      });
    }

    function syncTextarea() {
      var sorted = sortBrDates(Array.from(selected));
      textarea.value = sorted.join(',');
    }

    function renderTags() {
      tagsWrap.innerHTML = '';
      var sorted = sortBrDates(Array.from(selected));
      sorted.forEach(function (iso) {
        var tag = document.createElement('span');
        tag.style.cssText = 'background:#007bff;color:#fff;border-radius:12px;padding:2px 10px;font-size:12px;display:inline-flex;align-items:center;gap:4px;cursor:pointer;';
        tag.innerHTML = ptBrDisplay(iso) + ' <span style="font-weight:bold;">&times;</span>';
        tag.title = 'Remover ' + ptBrDisplay(iso);
        tag.addEventListener('click', function () {
          selected.delete(iso);
          syncTextarea();
          renderTags();
          renderGrid();
        });
        tagsWrap.appendChild(tag);
      });
    }

    function renderGrid() {
      grid.innerHTML = '';
      lblMes.textContent = MESES[viewMes] + ' ' + viewAno;

      // Cabeçalho dias da semana
      DIAS_SEQ.forEach(function (d) {
        var h = document.createElement('div');
        h.textContent = d;
        h.style.cssText = 'text-align:center;font-size:10px;font-weight:bold;color:#6c757d;padding:2px 0;';
        grid.appendChild(h);
      });

      var primeiro = new Date(viewAno, viewMes, 1);
      var inicioGrid = new Date(primeiro);
      inicioGrid.setDate(1 - primeiro.getDay()); // começa no domingo anterior

      for (var i = 0; i < 42; i++) {
        var d = new Date(inicioGrid);
        d.setDate(inicioGrid.getDate() + i);
        var br = dateToBr(d);
        var mesmomes = d.getMonth() === viewMes;

        var cell = document.createElement('div');
        cell.textContent = d.getDate();
        cell.dataset.iso = br;

        var sel = selected.has(br);
        cell.style.cssText = [
          'text-align:center;padding:5px 2px;border-radius:4px;font-size:12px;cursor:pointer;',
          'transition:background .15s;',
          sel ? 'background:#007bff;color:#fff;font-weight:bold;' :
            (mesmomes ? 'background:#f8f9fa;color:#343a40;' : 'background:none;color:#ced4da;')
        ].join('');

        if (mesmomes) {
          cell.addEventListener('mouseenter', function () {
            if (!selected.has(this.dataset.iso))
              this.style.background = '#cce5ff';
          });
          cell.addEventListener('mouseleave', function () {
            if (!selected.has(this.dataset.iso))
              this.style.background = '#f8f9fa';
          });
          cell.addEventListener('click', function () {
            var k = this.dataset.iso;
            if (selected.has(k)) selected.delete(k);
            else selected.add(k);
            syncTextarea();
            renderTags();
            renderGrid();
          });
        }
        grid.appendChild(cell);
      }
    }

    btnPrev.addEventListener('click', function () {
      viewMes--;
      if (viewMes < 0) { viewMes = 11; viewAno--; }
      renderGrid();
    });
    btnNext.addEventListener('click', function () {
      viewMes++;
      if (viewMes > 11) { viewMes = 0; viewAno++; }
      renderGrid();
    });

    renderGrid();
    renderTags();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[name="dias_cobertura"], #id_dias_cobertura').forEach(function (el) {
      buildWidget(el);
    });
  });
})();
