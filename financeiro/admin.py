# financeiro/admin.py

from django.utils.safestring import mark_safe
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import admin
from django.utils import timezone
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.urls import path

from .models import ContasAPagar, ContasAReceber, BaseSaldo, GerarFixo, Transferencia
from cadastros.models import Cliente


# ---------------------------------------------------------------------------
# Filtros de texto ocultos (sem lookups — processados pelo backend,
# mas não renderizados pela sidebar do Django/Jazzmin)
# ---------------------------------------------------------------------------
class _TextFilter(admin.SimpleListFilter):
    """Base: recebe valor via URL, filtra o queryset, não exibe choices na sidebar."""
    def lookups(self, request, model_admin):
        return ()

    def choices(self, changelist):
        return []

    def has_output(self):
        # Deve retornar True para que Django inclua o filtro no pipeline
        # e chame queryset() quando o parâmetro estiver na URL.
        return True

    def queryset(self, request, queryset):
        return queryset  # sobrescrito nas subclasses


class NotaSearchFilter(_TextFilter):
    title = 'Nota'
    parameter_name = 'nota_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(nota__icontains=self.value())


class FornecedorSearchFilter(_TextFilter):
    title = 'Fornecedor'
    parameter_name = 'forn_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(fornecedor__razao_social__icontains=self.value())


class ClienteSearchFilter(_TextFilter):
    title = 'Cliente'
    parameter_name = 'cli_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(cliente__razao_social__icontains=self.value())


class NomeSearchFilter(_TextFilter):
    title = 'Nome'
    parameter_name = 'nome_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(nome__icontains=self.value())


class UsuarioBaixaFilter(_TextFilter):
    title = 'Usuário da Baixa'
    parameter_name = 'usuario_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(usuario_baixa__icontains=self.value())


class FeitoporSearchFilter(_TextFilter):
    title = 'Feito Por'
    parameter_name = 'feito_q'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(criado_por__username__icontains=self.value())


# --- TELA CUSTOMIZADA: GERAR FIXOS MENSAIS NO MENU ---
@admin.register(GerarFixo)
class GerarFixoAdmin(admin.ModelAdmin):
    change_list_template = "admin/financeiro/gerar_fixos_mensais.html"

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.has_perm('financeiro.view_gerarfixo')

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.has_perm('financeiro.view_gerarfixo')

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def changelist_view(self, request, extra_context=None):
        from cadastros.models import Empresa, Banco, Cliente
        from financeiro.models import ContasAReceber
        from datetime import date

        clientes_fixos = Cliente.objects.filter(tipo='FIXO')
        empresas = Empresa.objects.all()
        bancos = Banco.objects.all()

        if request.method == 'POST':
            clientes_ids = request.POST.getlist('clientes_selecionados')
            contas_geradas = 0

            for cliente_id in clientes_ids:
                data_vencimento = request.POST.get(f'data_gerar_{cliente_id}')
                empresa_id = request.POST.get(f'empresa_id_{cliente_id}')
                banco_id = request.POST.get(f'banco_id_{cliente_id}')

                if data_vencimento and empresa_id and banco_id:
                    cliente_obj = Cliente.objects.get(id=cliente_id)
                    empresa_selecionada = Empresa.objects.get(id=empresa_id)
                    banco_selecionado = Banco.objects.get(id=banco_id)

                    ContasAReceber.objects.create(
                        cliente=cliente_obj,
                        empresa_prestadora=empresa_selecionada,
                        banco=banco_selecionado,
                        data_emissao=date.today(),
                        vencimento=data_vencimento,
                        valor=cliente_obj.valor_contrato,
                        status='PENDENTE',
                        observacoes='Gerado automaticamente via lote de Fixos Mensais.'
                    )
                    contas_geradas += 1

            self.message_user(request, f"Sucesso! {contas_geradas} Contas a Receber geradas.", messages.SUCCESS)
            return redirect(request.path)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Gerar Fixos Mensais',
            'clientes': clientes_fixos,
            'empresas': empresas,
            'bancos': bancos,
        }
        return render(request, self.change_list_template, context)


# --- FILTROS ---
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


class EmpresaPagadoraFilter(admin.SimpleListFilter):
    title = 'Empresa Pagadora'
    parameter_name = 'empresa_pagadora'

    def lookups(self, request, model_admin):
        empresas = ContasAPagar.objects.values_list(
            'empresa_pagadora__id', 'empresa_pagadora__nome'
        ).distinct().order_by('empresa_pagadora__nome')
        return [(id, nome) for id, nome in empresas if id and nome]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(empresa_pagadora__id=self.value())


class EmpresaPrestadoraFilter(admin.SimpleListFilter):
    title = 'Empresa Prestadora'
    parameter_name = 'empresa_prestadora'

    def lookups(self, request, model_admin):
        empresas = ContasAReceber.objects.values_list(
            'empresa_prestadora__id', 'empresa_prestadora__nome'
        ).distinct().order_by('empresa_prestadora__nome')
        return [(id, nome) for id, nome in empresas if id and nome]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(empresa_prestadora__id=self.value())


class StatusSaldoFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return BaseSaldo.objects.values_list('status', 'status').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class OrigemSaldoFilter(admin.SimpleListFilter):
    title = 'Origem'
    parameter_name = 'origem'

    def lookups(self, request, model_admin):
        return BaseSaldo.objects.values_list('origem', 'origem').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(origem=self.value())


class EmpresaSaldoFilter(admin.SimpleListFilter):
    title = 'Empresa'
    parameter_name = 'empresa'

    def lookups(self, request, model_admin):
        return BaseSaldo.objects.values_list('empresa', 'empresa').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(empresa=self.value())


class BancoSaldoFilter(admin.SimpleListFilter):
    title = 'Banco'
    parameter_name = 'banco'

    def lookups(self, request, model_admin):
        return BaseSaldo.objects.values_list('banco', 'banco').distinct()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(banco=self.value())


# --- AÇÕES EM MASSA ---
@admin.action(description='✅ Baixar/Pagar Selecionados')
def marcar_como_pago(modeladmin, request, queryset):
    hoje = timezone.now().date()
    for obj in queryset:
        obj.status = 'PAGO'
        obj.data_baixa = hoje
        obj.usuario_baixa = request.user
        obj.save()
    modeladmin.message_user(request, "Registros marcados como PAGO.")


@admin.action(description='❌ Cancelar Selecionados')
def marcar_como_cancelado(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = 'CANCELADO'
        obj.save()
    modeladmin.message_user(request, "Registros CANCELADOS.")


@admin.action(description='🔄 Voltar para Pendente')
def marcar_como_pendente(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = 'PENDENTE'
        obj.data_baixa = None
        obj.usuario_baixa = None
        obj.save()
    modeladmin.message_user(request, "Registros voltaram para PENDENTE.")


@admin.action(description="📅 Gerar duplicatas mensais (Fixos)")
def gerar_fixos_mensais(modeladmin, request, queryset):
    contas_criadas = 0
    for conta in queryset:
        if not conta.vencimento:
            continue
        nova_emissao = conta.data_emissao + relativedelta(months=1) if conta.data_emissao else None
        novo_vencimento = conta.vencimento + relativedelta(months=1)
        ContasAPagar.objects.create(
            fornecedor=conta.fornecedor,
            empresa_pagadora=conta.empresa_pagadora,
            banco=conta.banco,
            valor=conta.valor,
            data_emissao=nova_emissao,
            vencimento=novo_vencimento,
            status='PENDENTE',
        )
        contas_criadas += 1
    modeladmin.message_user(
        request,
        f"Sucesso! {contas_criadas} contas fixas foram geradas para o próximo mês.",
        messages.SUCCESS
    )


# --- 1. CONTAS A PAGAR ---
class ContasAPagarAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'fornecedor', 'vencimento', 'valor', 'status_visual', 'data_baixa', 'usuario_baixa')
    search_fields = ('fornecedor__razao_social', 'nota', 'observacoes')
    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        ('data_baixa', DateRangeFilter),
        EmpresaPagadoraFilter,
        NotaSearchFilter,
        FornecedorSearchFilter,
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente, gerar_fixos_mensais]

    def changelist_view(self, request, extra_context=None):
        extra = extra_context or {}
        extra['custom_filter_template'] = 'admin/financeiro/contasapagar/_filters.html'
        extra['empresas_opts'] = list(
            ContasAPagar.objects.select_related('empresa_pagadora')
            .values_list('empresa_pagadora__id', 'empresa_pagadora__nome')
            .distinct().order_by('empresa_pagadora__nome')
        )
        return super().changelist_view(request, extra_context=extra)

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO' and not obj.usuario_baixa:
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 2. CONTAS A RECEBER ---
class ContasAReceberAdmin(ImportExportModelAdmin):
    list_display = ('nota', 'cliente', 'vencimento', 'valor', 'status_visual', 'data_baixa', 'usuario_baixa')
    search_fields = ('cliente__razao_social', 'nota', 'observacoes')
    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        ('data_baixa', DateRangeFilter),
        EmpresaPrestadoraFilter,
        NotaSearchFilter,
        ClienteSearchFilter,
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente]

    def changelist_view(self, request, extra_context=None):
        extra = extra_context or {}
        extra['custom_filter_template'] = 'admin/financeiro/contasareceber/_filters.html'
        extra['empresas_opts'] = list(
            ContasAReceber.objects.select_related('empresa_prestadora')
            .values_list('empresa_prestadora__id', 'empresa_prestadora__nome')
            .distinct().order_by('empresa_prestadora__nome')
        )
        return super().changelist_view(request, extra_context=extra)

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO' and not obj.usuario_baixa:
            obj.usuario_baixa = request.user
        obj.save(request=request)


# --- 3. BASE DE SALDOS ---
class BaseSaldoAdmin(ImportExportModelAdmin):
    list_display = ('data_baixa', 'nome', 'valor', 'empresa', 'banco', 'usuario_baixa', 'origem')
    search_fields = ('nome', 'empresa', 'banco')
    list_filter = (
        ('data_baixa', DateRangeFilter),
        OrigemSaldoFilter,
        EmpresaSaldoFilter,
        BancoSaldoFilter,
        NomeSearchFilter,
        UsuarioBaixaFilter,
    )
    date_hierarchy = 'data_baixa'

    def changelist_view(self, request, extra_context=None):
        extra = extra_context or {}
        extra['custom_filter_template'] = 'admin/financeiro/basesaldo/_filters.html'
        extra['empresas_opts'] = list(BaseSaldo.objects.values_list('empresa', flat=True).distinct().order_by('empresa'))
        extra['bancos_opts']   = list(BaseSaldo.objects.values_list('banco',   flat=True).distinct().order_by('banco'))
        extra['origens_opts']  = list(BaseSaldo.objects.values_list('origem',  flat=True).distinct().order_by('origem'))
        extra['usuarios_opts'] = list(
            BaseSaldo.objects.exclude(usuario_baixa__isnull=True).exclude(usuario_baixa='')
            .values_list('usuario_baixa', flat=True).distinct().order_by('usuario_baixa')
        )
        return super().changelist_view(request, extra_context=extra)

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


# --- 4. TRANSFERÊNCIAS ---
class TransferenciaAdmin(admin.ModelAdmin):
    change_list_template = "admin/financeiro/transferencia/change_list.html"
    list_display = (
        'data', 'empresa', 'valor',
        'banco_origem', 'seta_visual', 'banco_destino',
        'status_badge', 'alerta_retorno', 'usuario_visual'
    )
    list_filter = ('status', 'banco_origem', 'banco_destino', FeitoporSearchFilter)
    search_fields = ('observacao', 'instrucao_retorno')
    readonly_fields = ('criado_por', 'data_devolucao')

    fieldsets = [
        ('Dados da Transferência', {
            'fields': (
                'data',
                'empresa',
                ('banco_origem', 'banco_destino'),
                'valor',
                'observacao',
            )
        }),
        ('Classificação e Controle', {
            'fields': (
                'status',
                'data_prevista_retorno',
                'instrucao_retorno',
                'data_devolucao',
            )
        }),
        ('Auditoria', {
            'fields': ('criado_por',),
            'classes': ('collapse',),
        }),
    ]

    def seta_visual(self, obj):
        return "➜"
    seta_visual.short_description = ""

    def usuario_visual(self, obj):
        return obj.criado_por.username if obj.criado_por else "-"
    usuario_visual.short_description = "Feito por"

    def status_badge(self, obj):
        cores = {
            'DEFINITIVA':     ('#28a745', '🟢 Definitiva'),
            'TEMP_PENDENTE':  ('#f39c12', '🟡 Pendente'),
            'TEMP_DEVOLVIDA': ('#3498db', '🔵 Devolvida'),
            'CANCELADA':      ('#6c757d', '⚫ Cancelada'),
        }
        cor, texto = cores.get(obj.status, ('#95a5a6', obj.status))
        return mark_safe(
            f'<span style="background:{cor}; color:white; padding:3px 8px; '
            f'border-radius:4px; font-size:11px; font-weight:bold; '
            f'white-space:nowrap;">{texto}</span>'
        )
    status_badge.short_description = "Classificação"

    def alerta_retorno(self, obj):
        hoje = date.today()

        if obj.status == 'DEFINITIVA':
            return mark_safe(
                '<span style="background:#28a745; color:white; padding:3px 8px; '
                'border-radius:4px; font-size:11px; font-weight:bold;">✅ OK</span>'
            )

        if obj.status == 'CANCELADA':
            return mark_safe(
                '<span style="background:#6c757d; color:white; padding:3px 8px; '
                'border-radius:4px; font-size:11px; font-weight:bold;">⚫ Cancelada</span>'
            )

        if obj.status == 'TEMP_DEVOLVIDA':
            data_dev = obj.data_devolucao.strftime('%d/%m/%Y') if obj.data_devolucao else '-'
            return mark_safe(
                f'<span style="background:#3498db; color:white; padding:3px 8px; '
                f'border-radius:4px; font-size:11px; font-weight:bold;">'
                f'🔵 Devolvida em {data_dev}</span>'
            )

        # TEMP_PENDENTE — verifica vencimento
        if obj.status == 'TEMP_PENDENTE':
            if not obj.data_prevista_retorno:
                return mark_safe(
                    '<span style="background:#e67e22; color:white; padding:3px 8px; '
                    'border-radius:4px; font-size:11px; font-weight:bold;">'
                    '⚠️ Sem data prevista</span>'
                )
            if obj.data_prevista_retorno < hoje:
                dias = (hoje - obj.data_prevista_retorno).days
                return mark_safe(
                    f'<span style="background:#dc3545; color:white; padding:3px 8px; '
                    f'border-radius:4px; font-size:11px; font-weight:bold;">'
                    f'🔴 Vencida há {dias} dia(s)</span>'
                )
            dias_restantes = (obj.data_prevista_retorno - hoje).days
            return mark_safe(
                f'<span style="background:#f39c12; color:white; padding:3px 8px; '
                f'border-radius:4px; font-size:11px; font-weight:bold;">'
                f'🟡 Retorna em {dias_restantes} dia(s)</span>'
            )

        return "-"
    alerta_retorno.short_description = "Alerta de Retorno"

    def changelist_view(self, request, extra_context=None):
        from cadastros.models import Banco
        extra = extra_context or {}
        extra['bancos_opts'] = list(Banco.objects.values_list('id', 'nome').order_by('nome'))
        extra['usuarios_opts'] = list(
            Transferencia.objects.exclude(criado_por=None)
            .values_list('criado_por__id', 'criado_por__username')
            .distinct().order_by('criado_por__username')
        )
        return super().changelist_view(request, extra_context=extra)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                'criado_por', 'data_devolucao',
                'data', 'valor', 'banco_origem',
                'banco_destino', 'empresa', 'observacao'
            )
        return ('criado_por', 'data_devolucao')


# --- REGISTROS FINAIS ---
admin.site.register(ContasAPagar, ContasAPagarAdmin)
admin.site.register(ContasAReceber, ContasAReceberAdmin)
admin.site.register(BaseSaldo, BaseSaldoAdmin)
admin.site.register(Transferencia, TransferenciaAdmin)