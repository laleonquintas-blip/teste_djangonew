"""
URL configuration for teste_django project.
"""
from django.contrib import admin
from django.urls import path
from financeiro.views import get_fornecedor_info, dashboard_financeiro, gerar_fixos_mensais, ajustar_saldos_bancos, fluxo_de_caixa
from extras.views import cloudinary_usage_api, cloudinary_storage_page
from core.views import trocar_senha_obrigatoria

# --- PERSONALIZAÇÃO DO SISTEMA MALUPE ---
admin.site.site_header = "Sistema Financeiro Malupe"
admin.site.site_title = "Malupe Admin"
admin.site.index_title = "Painel de Gestão"

urlpatterns = [
    # 1. ROTAS CUSTOMIZADAS (Devem vir primeiro!)
    path('admin/trocar-senha/', trocar_senha_obrigatoria, name='trocar_senha_obrigatoria'),
    path('admin/financeiro/dashboard-gerencial/', dashboard_financeiro, name='dashboard_gerencial'),
    path('admin/financeiro/gerar-fixos/', gerar_fixos_mensais, name='gerar_fixos_mensais'),
    path('admin/financeiro/ajustar-saldos/', ajustar_saldos_bancos, name='ajustar_saldos'),
    path('admin/financeiro/fluxo-de-caixa/', fluxo_de_caixa, name='fluxo_de_caixa'),
    path('admin/api/cloudinary-usage/', cloudinary_usage_api, name='api_cloudinary_usage'),
    path('admin/workflow/cloudinary-storage/', cloudinary_storage_page, name='cloudinary_storage_page'),

    # 2. API
    path('api/fornecedor-info/', get_fornecedor_info, name='api_fornecedor_info'),

    # 3. ROTA PADRÃO DO ADMIN (Deve vir SEMPRE por último!)
    path('admin/', admin.site.urls),
]
