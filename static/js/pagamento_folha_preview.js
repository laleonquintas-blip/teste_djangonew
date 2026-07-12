(function () {
  var API = '/api/colaboradores-folha/';

  function fmt(v) {
    if (v === null || v === undefined || v === 'None' || v === '') return '-';
    var n = parseFloat(v);
    if (isNaN(n)) return '-';
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function render(cols) {
    var c = document.getElementById('preview-colaboradores');
    if (!c) return;

    if (!cols || !cols.length) {
      c.innerHTML = '<p style="color:#888;padding:8px 0">Nenhum colaborador ativo nesta folha.</p>';
      updateTotal(0);
      return;
    }

    var tot = 0, sub = 0, banco = null;
    var rows = '';
    var td = 'style="padding:9px 14px;color:#212529;border-bottom:1px solid #dee2e6;white-space:nowrap;"';

    cols.forEach(function (x, i) {
      var v = parseFloat(x.valor_atual) || 0;
      tot += v;

      if (x.banco !== banco) {
        if (banco !== null) {
          rows += '<tr style="background:#f8f9fa;">'
            + '<td colspan="3" style="padding:7px 14px;text-align:right;color:#555;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;">Subtotal ' + banco + '</td>'
            + '<td style="padding:7px 14px;color:#212529;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;"></td>'
            + '<td style="padding:7px 14px;color:#212529;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;">' + fmt(sub) + '</td>'
            + '<td style="padding:7px 14px;border-bottom:1px solid #dee2e6;"></td>'
            + '</tr>';
        }
        banco = x.banco; sub = 0;
        rows += '<tr style="background:#e9ecef;">'
          + '<td colspan="6" style="padding:8px 14px;font-weight:700;color:#343a40;border-bottom:1px solid #dee2e6;">🏦 ' + banco + '</td>'
          + '</tr>';
      }

      sub += v;
      rows += '<tr>'
        + '<td ' + td + '>' + x.nome + ' &mdash; CPF: ' + x.cpf + '</td>'
        + '<td ' + td + '>' + x.filial + '</td>'
        + '<td ' + td + '>Ag: ' + x.agencia + ' | Cc: ' + x.conta + '</td>'
        + '<td ' + td + '>' + fmt(x.valor_anterior) + '</td>'
        + '<td ' + td + '>' + fmt(x.valor_atual) + '</td>'
        + '<td ' + td + '>-</td>'
        + '</tr>';

      if (i === cols.length - 1) {
        rows += '<tr style="background:#f8f9fa;">'
          + '<td colspan="3" style="padding:7px 14px;text-align:right;color:#555;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;">Subtotal ' + banco + '</td>'
          + '<td style="padding:7px 14px;color:#212529;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;"></td>'
          + '<td style="padding:7px 14px;color:#212529;font-weight:600;border-bottom:1px solid #dee2e6;white-space:nowrap;">' + fmt(sub) + '</td>'
          + '<td style="padding:7px 14px;border-bottom:1px solid #dee2e6;"></td>'
          + '</tr>';
        rows += '<tr style="background:#1a6e4a;">'
          + '<td colspan="3" style="padding:10px 14px;text-align:right;color:#fff;font-weight:700;white-space:nowrap;">TOTAL GERAL</td>'
          + '<td style="padding:10px 14px;color:#fff;font-weight:700;"></td>'
          + '<td style="padding:10px 14px;color:#fff;font-weight:700;font-size:.95rem;">' + fmt(tot) + '</td>'
          + '<td style="padding:10px 14px;"></td>'
          + '</tr>';
      }
    });

    // Sobe no DOM até o card-body/p-5 para tomar toda a largura
    var target = c;
    var el = c;
    for (var i = 0; i < 12; i++) {
      el = el.parentElement;
      if (!el) break;
      if (el.classList && (el.classList.contains('p-5') || el.classList.contains('card-body'))) {
        target = el; break;
      }
    }

    var thStyle = 'padding:10px 14px;text-align:left;font-weight:600;color:#212529;white-space:nowrap;border-bottom:2px solid #dee2e6;';
    var tdStyle = 'padding:9px 14px;color:#212529;border-bottom:1px solid #dee2e6;white-space:nowrap;';

    var html = '<table style="width:100%;border-collapse:collapse;font-size:.875rem;">'
      + '<thead><tr>'
      + '<th style="' + thStyle + '">Colaborador</th>'
      + '<th style="' + thStyle + '">Filial</th>'
      + '<th style="' + thStyle + '">Banco / Ag / Conta</th>'
      + '<th style="' + thStyle + '">Valor anterior</th>'
      + '<th style="' + thStyle + '">Valor atual</th>'
      + '<th style="' + thStyle + '">Justificativa da diferença</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table>';

    if (target !== c) {
      target.style.padding = '0';
      target.innerHTML = html;
    } else {
      c.innerHTML = html;
    }

    updateTotal(tot);
  }

  function updateTotal(tot) {
    var el = document.getElementById('preview-total-folha');
    if (el) el.innerHTML = tot > 0
      ? 'R$ ' + tot.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : '—';
  }

  function load(id) {
    var c = document.getElementById('preview-colaboradores');
    if (!c) return;
    if (!id) {
      c.innerHTML = '<p style="color:#aaa;padding:8px 0">Selecione uma folha para ver os colaboradores.</p>';
      updateTotal(0);
      return;
    }
    c.innerHTML = '<p style="color:#888;padding:8px 0">Carregando...</p>';
    fetch(API + '?folha_id=' + id)
      .then(function (r) { return r.json(); })
      .then(function (d) { render(d.colaboradores); })
      .catch(function () {
        var c2 = document.getElementById('preview-colaboradores');
        if (c2) c2.innerHTML = '<p style="color:red;padding:8px 0">Erro ao carregar colaboradores.</p>';
      });
  }

  function init() {
    var sel = document.getElementById('id_folha');
    if (!sel) return;
    var $ = window.jQuery || (window.django && window.django.jQuery);
    if ($) {
      $(sel).on('select2:select select2:clear change', function () { load($(this).val()); });
    } else {
      sel.addEventListener('change', function () { load(this.value); });
    }
    function tryLoad(n) {
      var val = sel.value || ($ ? $(sel).val() : '');
      if (val) { load(val); } else if (n > 0) { setTimeout(function () { tryLoad(n - 1); }, 300); }
    }
    tryLoad(5);
  }

  window.addEventListener('load', function () { setTimeout(init, 300); });
})();
