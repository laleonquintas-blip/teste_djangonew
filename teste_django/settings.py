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
    'https://app.malupe.com.br',
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
    'rangefilter',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
        "financeiro.Transferencia": "fas fa-exchange-alt",
        "workflow.Despesa": "fas fa-tasks",
    },

    # 1. ADICIONA LINKS CUSTOMIZADOS NO MENU FINANCEIRO
    "custom_links": {
        "financeiro": [
            {
                "name": "Dashboard Gerencial",
                "url": "/admin/financeiro/dashboard-gerencial/",
                "icon": "fas fa-chart-pie",
                "new_window": False,
                "permissions": ["financeiro.view_contasapagar"]
            },
            {
                "name": "Ajuste de Saldos",
                "url": "/admin/financeiro/ajustar-saldos/",
                "icon": "fas fa-sliders-h",
                "new_window": False,
                "permissions": ["auth.add_user"]
            }
        ]
    },

    # 2. ESCONDE O DASHBOARD DO TOPO (evita duplicata)
    "topmenu_links": [
        {"name": "Início", "url": "admin:index", "permissions": ["auth.view_user"]},
    ],

    "show_ui_builder": True,

}
# settings.py
STATIC_ROOT = BASE_DIR / 'staticfiles'

GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE = os.path.join(BASE_DIR, 'credenciais_google.json')
GOOGLE_DRIVE_STORAGE_MEDIA_ROOT = 'Comprovantes_Sistema'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


