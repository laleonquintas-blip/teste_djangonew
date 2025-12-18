# financeiro/admin.py

from django.contrib import admin
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from .models import ContasAPagar, ContasAReceber, BaseSaldo


# --- 1. CONTAS A PAGAR ---
class ContasAPagarAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'fornecedor', 'vencimento', 'valor', 'status', 'data_baixa', 'usuario_baixa')

    # BUSCA (LUPA): Digite aqui o Nome do Fornecedor ou a Nota
    search_fields = ('nota', 'fornecedor__razao_social')

    # FILTROS LATERAIS (Sem fornecedor, para não travar)
    list_filter = (
        ('vencimento', DateRangeFilter),  # 1. Por Vencimento (De/Até)
        ('data_emissao', DateRangeFilter),  # 2. Por Emissão (De/Até)
        'status',  # 3. Status
        'empresa_pagadora',  # 4. Empresa Pagadora
    )

    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO':
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 2. CONTAS A RECEBER ---
class ContasAReceberAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'cliente', 'vencimento', 'valor', 'status', 'data_baixa', 'usuario_baixa')

    # BUSCA (LUPA): Digite aqui o Nome do Cliente ou a Nota
    search_fields = ('nota', 'cliente__razao_social')

    # FILTROS LATERAIS (Sem cliente)
    list_filter = (
        ('vencimento', DateRangeFilter),  # 1. Por Vencimento (De/Até)
        ('data_emissao', DateRangeFilter),  # 2. Por Emissão (De/Até)
        'status',  # 3. Status
        'empresa_prestadora',  # 4. Empresa Prestadora
    )

    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO':
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 3. BASE DE SALDOS ---
class BaseSaldoAdmin(ImportExportModelAdmin):
    list_display = ('data_baixa', 'nome', 'valor', 'empresa', 'banco', 'usuario_baixa', 'origem')

    # BUSCA (LUPA): Nome, Empresa ou Banco
    search_fields = ('nome', 'empresa', 'banco')

    # FILTROS LATERAIS
    list_filter = (
        ('data_baixa', DateRangeFilter),  # 1. Por Data Baixa (De/Até)
        'status',  # 2. Status
        'origem',  # 3. Origem
        'empresa',  # 4. Empresa
        'banco',  # 5. Banco
    )

    date_hierarchy = 'data_baixa'

    # Permissões (Somente Leitura)
    def has_add_permission(self, request): return False

    def has_change_permission(self, request, obj=None): return False

    def has_delete_permission(self, request, obj=None): return False


admin.site.register(ContasAPagar, ContasAPagarAdmin)
admin.site.register(ContasAReceber, ContasAReceberAdmin)
admin.site.register(BaseSaldo, BaseSaldoAdmin)