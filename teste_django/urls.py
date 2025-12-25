"""
URL configuration for teste_django project.
"""
from django.contrib import admin
from django.urls import path

# Importamos as duas views: a antiga (API) e a nova (Dashboard)
from financeiro.views import get_fornecedor_info, dashboard_financeiro

# --- PERSONALIZAÇÃO DO SISTEMA MALUPE ---
admin.site.site_header = "Sistema Financeiro Malupe"  # Texto na Barra Azul
admin.site.site_title = "Malupe Admin"                # Texto na Aba do Navegador
admin.site.index_title = "Painel de Gestão"           # Título da Página Principal

# --- ATIVAÇÃO DO DASHBOARD PERSONALIZADO ---
# Esta linha sobrescreve a "Home" do Admin padrão pela nossa view de gráficos
admin.site.index = dashboard_financeiro

urlpatterns = [
    # A URL do admin continua a mesma, mas internamente ela chama o dashboard agora
    path('admin/', admin.site.urls),

    # API para o Workflow (JavaScript vai chamar aqui)
    path('api/fornecedor-info/', get_fornecedor_info, name='api_fornecedor_info'),
]