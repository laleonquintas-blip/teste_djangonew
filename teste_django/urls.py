"""
URL configuration for teste_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from financeiro.views import get_fornecedor_info

# --- PERSONALIZAÇÃO DO SISTEMA MALUPE ---
admin.site.site_header = "Sistema Financeiro Malupe"  # Texto na Barra Azul
admin.site.site_title = "Malupe Admin"                # Texto na Aba do Navegador
admin.site.index_title = "Painel de Gestão"           # Título da Página Principal

urlpatterns = [
    path('admin/', admin.site.urls),
# API para o Workflow (JavaScript vai chamar aqui)
    path('api/fornecedor-info/', get_fornecedor_info, name='api_fornecedor_info'),
]
