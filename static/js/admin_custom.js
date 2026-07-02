// Executa fn imediatamente se o DOM já estiver pronto, ou aguarda DOMContentLoaded
function onReady(fn) {
    if (document.readyState !== 'loading') {
        fn();
    } else {
        document.addEventListener('DOMContentLoaded', fn);
    }
}

// Aplica tema salvo antes do render (anti-flash)
if (localStorage.getItem('malupe_theme') === 'dark') {
    document.body && document.body.classList.add('dark-mode');
}

onReady(function () {

    // ── 1. Aplica tema salvo ──────────────────────────────────────────────────
    if (localStorage.getItem('malupe_theme') === 'dark') {
        document.body.classList.add('dark-mode');
    }

    // ── 1b. Força sidebar sempre visível (impede AdminLTE de colapsar para o topo) ──
    document.body.classList.remove('sidebar-collapse', 'sidebar-mini-xs', 'sidebar-mini');
    try {
        localStorage.removeItem('lte3|sidenav|collapsed');
        localStorage.removeItem('lte|sidenav|collapsed');
    } catch (e) {}


    // ── 2. Injeta botão dark/light na navbar ─────────────────────────────────
    var isDark = document.body.classList.contains('dark-mode');
    var navRight = document.querySelector('.navbar-nav.ml-auto');

    if (navRight && !document.getElementById('theme-toggle-btn')) {
        var li  = document.createElement('li');
        li.className = 'nav-item';

        var btn = document.createElement('button');
        btn.id    = 'theme-toggle-btn';
        btn.type  = 'button';
        btn.title = 'Alternar modo escuro / claro';
        btn.innerHTML = isDark ? '&#9728;&#65039; Claro' : '&#127769; Escuro';

        btn.addEventListener('click', function () {
            var dark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('malupe_theme', dark ? 'dark' : 'light');
            btn.innerHTML = dark ? '&#9728;&#65039; Claro' : '&#127769; Escuro';
        });

        li.appendChild(btn);
        navRight.insertBefore(li, navRight.firstChild);
    }

    // ── 2b. Bloqueia duplo envio de formulário ───────────────────────────────
    document.querySelectorAll('form[method="post"]').forEach(function (form) {
        var enviado = false;
        form.addEventListener('submit', function (e) {
            if (enviado) {
                e.preventDefault();
                e.stopImmediatePropagation();
                return false;
            }
            enviado = true;
            form.querySelectorAll('input[type="submit"], button[type="submit"]').forEach(function (btn) {
                btn.disabled = true;
                btn.style.opacity = '0.6';
                btn.style.cursor = 'not-allowed';
            });
        });
    });

    // ── 3. Remove campo fantasma 'q' da sidebar ──────────────────────────────
    document.querySelectorAll('#changelist-filter input[name="q"]').forEach(function (el) {
        el.remove();
    });

    // ── 4. Remove botão pesquisar duplicado no rodapé ────────────────────────
    document.querySelectorAll('#changelist-filter form > div > input[type="submit"]').forEach(function (el) {
        el.style.setProperty('display', 'none', 'important');
    });

    // ── 5. Estiliza botões do rangefilter ────────────────────────────────────
    document.querySelectorAll('.admindatefilter .controls a').forEach(function (link) {
        Object.assign(link.style, {
            display: 'inline-block', width: '48%', textAlign: 'center',
            backgroundColor: '#17a2b8', color: 'white', padding: '10px',
            borderRadius: '4px', textDecoration: 'none',
            fontWeight: 'bold', textTransform: 'uppercase', fontSize: '0.75rem'
        });
        link.innerHTML = 'LIMPAR';
    });

    // Confirmação de duplicidade: esconde o campo e só exibe quando há erro de duplicidade
onReady(function () {
    var row = document.querySelector('.field-confirmar_duplicidade');
    if (!row) return;
    var erros = document.querySelectorAll('.errornote, ul.errorlist');
    var temDuplicidade = false;
    erros.forEach(function (el) {
        if (el.textContent.indexOf('duplicidade') !== -1 || el.textContent.indexOf('Possível') !== -1) {
            temDuplicidade = true;
        }
    });
    if (temDuplicidade) {
        row.style.background = '#fff8e1';
        row.style.border = '2px solid #ffc107';
        row.style.borderRadius = '6px';
        row.style.padding = '12px';
        row.style.marginTop = '12px';
    } else {
        row.style.display = 'none';
    }
});

document.querySelectorAll('.admindatefilter .controls input[type="submit"], .admindatefilter .controls button').forEach(function (btn) {
        Object.assign(btn.style, {
            width: '48%', backgroundColor: '#007bff', color: 'white',
            border: 'none', padding: '10px', borderRadius: '4px',
            fontWeight: 'bold', textTransform: 'uppercase', fontSize: '0.75rem', cursor: 'pointer'
        });
    });

});
