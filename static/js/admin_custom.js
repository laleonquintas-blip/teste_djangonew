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

    // Modal de confirmação de duplicidade
onReady(function () {
    var erros = document.querySelectorAll('.errornote, ul.errorlist li');
    var msgDuplicidade = '';
    erros.forEach(function (el) {
        if (el.textContent.indexOf('Possível duplicidade') !== -1) {
            msgDuplicidade = el.textContent.trim();
        }
    });
    if (!msgDuplicidade) return;

    // Cria o modal
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';

    var box = document.createElement('div');
    box.style.cssText = 'background:#fff;border-radius:12px;padding:32px 28px;max-width:480px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.2);';
    box.innerHTML = '<div style="font-size:2rem;text-align:center;">⚠️</div>'
        + '<h3 style="text-align:center;color:#856404;margin:12px 0 8px;">Possível Duplicidade</h3>'
        + '<p style="color:#555;font-size:0.95rem;margin-bottom:24px;">' + msgDuplicidade.replace('Se desejar salvar mesmo assim, marque a opção abaixo e clique em Salvar novamente.', '') + '</p>'
        + '<p style="color:#333;font-weight:600;text-align:center;margin-bottom:20px;">Deseja salvar mesmo assim?</p>'
        + '<div style="display:flex;gap:12px;">'
        + '<button id="dup-sim" style="flex:1;padding:12px;background:#dc3545;color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:700;cursor:pointer;">Sim, salvar mesmo assim</button>'
        + '<button id="dup-nao" style="flex:1;padding:12px;background:#6c757d;color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:700;cursor:pointer;">Não, cancelar</button>'
        + '</div>';

    overlay.appendChild(box);
    document.body.appendChild(overlay);

    document.getElementById('dup-nao').addEventListener('click', function () {
        overlay.remove();
    });

    document.getElementById('dup-sim').addEventListener('click', function () {
        var campo = document.querySelector('input[name="confirmar_duplicidade"]');
        if (campo) campo.value = 'on';
        overlay.remove();
        document.querySelector('[name="_save"]').click();
    });
});

document.querySelectorAll('.admindatefilter .controls input[type="submit"], .admindatefilter .controls button').forEach(function (btn) {
        Object.assign(btn.style, {
            width: '48%', backgroundColor: '#007bff', color: 'white',
            border: 'none', padding: '10px', borderRadius: '4px',
            fontWeight: 'bold', textTransform: 'uppercase', fontSize: '0.75rem', cursor: 'pointer'
        });
    });

});
