document.addEventListener("DOMContentLoaded", function() {
    // 1. CAÇA-FANTASMA: Remove o campo de texto 'q' solto na barra lateral
    const ghostInputs = document.querySelectorAll('#changelist-filter input[name="q"]');
    ghostInputs.forEach(function(input) {
        input.style.setProperty('display', 'none', 'important');
        input.style.setProperty('visibility', 'hidden', 'important');
        input.style.setProperty('height', '0', 'important');
        input.style.setProperty('padding', '0', 'important');
        input.style.setProperty('margin', '0', 'important');
        // Para garantir, removemos do HTML
        input.remove();
    });

    // 2. REMOVE O BOTÃO DE PESQUISAR DE BAIXO (O marcado com X)
    // Procuramos o botão de submit que está solto no formulário, fora dos controles de data
    const bottomButtons = document.querySelectorAll('#changelist-filter form > div > input[type="submit"]');
    bottomButtons.forEach(function(btn) {
        btn.style.setProperty('display', 'none', 'important');
    });

    // 3. ESTILIZA O LINK "LIMPAR" PARA PARECER UM BOTÃO AZUL
    // O Django Range Filter cria um link <a> para limpar. Vamos transformá-lo em botão visualmente.
    const clearLinks = document.querySelectorAll('.admindatefilter .controls a');
    clearLinks.forEach(function(link) {
        link.style.display = "inline-block";
        link.style.width = "48%";
        link.style.textAlign = "center";
        link.style.backgroundColor = "#17a2b8"; // Azul Turquesa
        link.style.color = "white";
        link.style.padding = "10px";
        link.style.borderRadius = "4px";
        link.style.textDecoration = "none";
        link.style.fontWeight = "bold";
        link.style.textTransform = "uppercase";
        link.style.fontSize = "0.75rem";
        link.innerHTML = "LIMPAR"; // Garante que o texto seja legível
    });

    // 4. ESTILIZA O BOTÃO "PESQUISAR" DE CIMA
    const topSearchButtons = document.querySelectorAll('.admindatefilter .controls input[type="submit"], .admindatefilter .controls button');
    topSearchButtons.forEach(function(btn) {
        btn.style.width = "48%";
        btn.style.backgroundColor = "#007bff"; // Azul Principal
        btn.style.color = "white";
        btn.style.border = "none";
        btn.style.padding = "10px";
        btn.style.borderRadius = "4px";
        btn.style.fontWeight = "bold";
        btn.style.textTransform = "uppercase";
        btn.style.fontSize = "0.75rem";
        btn.style.cursor = "pointer";
    });

    console.log("Admin Custom JS: Limpeza realizada com sucesso.");
});
/* Esconde o link padrão "Dashboard" do sidebar do Jazzmin */
.nav-sidebar > .nav-item:has(> a.nav-link.active[href="/admin/"]),
.nav-sidebar > .nav-item:first-of-type {
    display: none !important;
}
"""
Django settings for teste_django project.
Arquivo CONFIGURADO PARA LER TEMPLATES PERSONALIZADOS.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = 'django-insecure-f$v=e=-9c-1&b)fskdf-isz5c(p=t!g%+6bg*txhjf6gp$u$ll'

DEBUG = True

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://semiacademic-sightless-hoa.ngrok-free.dev',
]

# Application definition
INSTALLED_APPS = [
    'extras',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Meus Apps
    'core',
    'cadastros',
    'financeiro',
    'workflow',
    'import_export',
    'rangefilter'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'teste_django.urls'

# AQUI ESTÁ A CHAVE PARA O HTML FUNCIONAR
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # <--- O Django vai ler seu base_site.html aqui
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'teste_django.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

AUTH_USER_MODEL = 'core.UsuarioCustomizado'

# ==============================================================================
# CONFIGURAÇÕES DO JAZZMIN
# ==============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "Malupe Admin",
    "site_header": "Malupe",
    "site_brand": "Painel Malupe",
    "site_logo": "img/logo.jpg",
    "login_logo": "img/logo.jpg",
    "site_logo_classes": "img-fluid",
    "welcome_sign": "Acesso do Colaborador Malupe",
    "copyright": "Malupe Ltda",
    "search_model": ["cadastros.Cliente"],

    "custom_css": "css/admin_custom.css",
    "custom_js": "js/admin_custom.js",

    "show_sidebar": True,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "order_with_respect_to": ["workflow", "financeiro", "cadastros", "core"],

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "cadastros.Cliente": "fas fa-user-tie",
        "cadastros.Fornecedor": "fas fa-truck",
        "financeiro.ContasAPagar": "fas fa-money-bill-wave",
        "financeiro.ContasAReceber": "fas fa-hand-holding-usd",
        "financeiro.BaseSaldo": "fas fa-chart-line",
        "workflow.Despesa": "fas fa-tasks",
    },

    # 1. ADICIONA O PAINEL FINANCEIRO NO MENU FINANCEIRO
    "custom_links": {
    "financeiro": [{
        "name": "Painel Financeiro",
        "url": "/admin/",
        "icon": "fas fa-chart-bar",
        "new_window": False,
    }]
},

    # 2. ESCONDE O DASHBOARD DO TOPO (evita duplicata)
    "topmenu_links": [
        {"name": "Início", "url": "admin:index", "permissions": ["auth.view_user"]},
    ],

    "show_ui_builder": True,

}
# settings.py
STATIC_ROOT = BASE_DIR / 'staticfiles'

/* Esconde o item Dashboard padrão do Jazzmin */
.nav-sidebar .nav-item:first-child {
    display: none !important;
}
