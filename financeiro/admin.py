# financeiro/admin.py

from django.contrib import admin
from django.utils import timezone
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from .models import ContasAPagar, ContasAReceber, BaseSaldo


# --- FILTRO PERSONALIZADO (Situação Detalhada) ---
class StatusFilter(admin.SimpleListFilter):
    title = 'Situação Detalhada'
    parameter_name = 'status_real'

    def lookups(self, request, model_admin):
        return (
            ('VENCIDO', '🔴 Vencido (Pendente)'),
            ('A_VENCER', '🔵 A Vencer (Pendente)'),
            ('PAGO', '🟢 Pago'),
            ('CANCELADO', '⚫ Cancelado'),
        )

    def queryset(self, request, queryset):
        hoje = timezone.now().date()
        if self.value() == 'VENCIDO':
            return queryset.filter(status='PENDENTE', vencimento__lt=hoje)
        if self.value() == 'A_VENCER':
            return queryset.filter(status='PENDENTE', vencimento__gte=hoje)
        if self.value() == 'PAGO':
            return queryset.filter(status='PAGO')
        if self.value() == 'CANCELADO':
            return queryset.filter(status='CANCELADO')


# --- AÇÕES EM MASSA ---
@admin.action(description='✅ Baixar/Pagar Selecionados')
def marcar_como_pago(modeladmin, request, queryset):
    queryset.update(status='PAGO', data_baixa=timezone.now().date(), usuario_baixa=request.user)
    modeladmin.message_user(request, f"Registros marcados como PAGO.")


@admin.action(description='❌ Cancelar Selecionados')
def marcar_como_cancelado(modeladmin, request, queryset):
    queryset.update(status='CANCELADO')
    modeladmin.message_user(request, f"Registros CANCELADOS.")


@admin.action(description='🔄 Voltar para Pendente')
def marcar_como_pendente(modeladmin, request, queryset):
    queryset.update(status='PENDENTE', data_baixa=None, usuario_baixa=None)
    modeladmin.message_user(request, f"Registros voltaram para PENDENTE.")


# --- 1. CONTAS A PAGAR ---
class ContasAPagarAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'fornecedor', 'vencimento', 'valor', 'status_visual', 'data_baixa', 'usuario_baixa')

    # ATIVE A BUSCA NOVAMENTE (O CSS vai esconder o duplicado da lateral)
    search_fields = ('nota', 'fornecedor__razao_social')

    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        'empresa_pagadora',
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente]

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO' and not obj.usuario_baixa:
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 2. CONTAS A RECEBER ---
class ContasAReceberAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'cliente', 'vencimento', 'valor', 'status_visual', 'data_baixa', 'usuario_baixa')

    # ATIVE A BUSCA NOVAMENTE
    search_fields = ('nota', 'cliente__razao_social')

    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        'empresa_prestadora',
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente]

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO' and not obj.usuario_baixa:
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 3. BASE DE SALDOS ---
class BaseSaldoAdmin(ImportExportModelAdmin):
    list_display = ('data_baixa', 'nome', 'valor', 'empresa', 'banco', 'usuario_baixa', 'origem')

    # Mantive aqui pois BaseSaldo geralmente não tem conflito, mas pode remover se quiser
    search_fields = ('nome', 'empresa', 'banco')

    list_filter = (
        ('data_baixa', DateRangeFilter),
        'status',
        'origem',
        'empresa',
        'banco',
    )
    date_hierarchy = 'data_baixa'

    def has_add_permission(self, request): return False

    def has_change_permission(self, request, obj=None): return False

    def has_delete_permission(self, request, obj=None): return False


admin.site.register(ContasAPagar, ContasAPagarAdmin)
admin.site.register(ContasAReceber, ContasAReceberAdmin)
admin.site.register(BaseSaldo, BaseSaldoAdmin)