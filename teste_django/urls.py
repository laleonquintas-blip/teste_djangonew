"""
URL configuration for teste_django project.
"""
from django.contrib import admin
from django.urls import path
from financeiro.views import get_fornecedor_info, dashboard_financeiro, gerar_fixos_mensais, ajustar_saldos_bancos, fluxo_de_caixa
from extras.views import cloudinary_usage_api, cloudinary_storage_page
from core.views import trocar_senha_obrigatoria
from workflow.views import relatorio_coberturas, exportar_coberturas_detalhado, painel_sla, painel_sla_tabela, api_colaborador_info
from monitoramento_rh.views import api_colaboradores_folha

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
    path('admin/monitoramento-rh/coberturas/', relatorio_coberturas, name='relatorio_coberturas'),
    path('admin/monitoramento-rh/coberturas/exportar/', exportar_coberturas_detalhado, name='exportar_coberturas_detalhado'),
    path('admin/workflow/painel-sla/', painel_sla, name='painel_sla'),
    path('admin/workflow/painel-sla/tabela/', painel_sla_tabela, name='painel_sla_tabela'),

    # 2. API
    path('api/fornecedor-info/', get_fornecedor_info, name='api_fornecedor_info'),
    path('api/colaborador-info/', api_colaborador_info, name='api_colaborador_info'),
    path('api/colaboradores-folha/', api_colaboradores_folha, name='api_colaboradores_folha'),

    # 3. ROTA PADRÃO DO ADMIN (Deve vir SEMPRE por último!)
    path('admin/', admin.site.urls),
]
