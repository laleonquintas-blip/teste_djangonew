# financeiro/admin.py

from django.utils.safestring import mark_safe
from django.utils.html import format_html
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import admin
from django.utils import timezone
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.urls import path

from .models import ContasAPagar, ContasAReceber, BaseSaldo, GerarFixo, Transferencia, SaldoSupervisor, MovimentacaoSupervisor
from .resources import ContasAPagarResource, ContasAReceberResource
from cadastros.models import Cliente
from django.contrib.auth.models import Group
from core.models import UsuarioCustomizado


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

            erros = []
            for cliente_id in clientes_ids:
                data_vencimento = request.POST.get(f'data_gerar_{cliente_id}')
                empresa_id = request.POST.get(f'empresa_id_{cliente_id}')
                banco_id = request.POST.get(f'banco_id_{cliente_id}')

                if data_vencimento and empresa_id and banco_id:
                    cliente_obj = Cliente.objects.get(id=cliente_id)

                    if not cliente_obj.valor_contrato:
                        erros.append(f"{cliente_obj.razao_social}: sem Valor do Contrato cadastrado.")
                        continue

                    empresa_selecionada = Empresa.objects.get(id=empresa_id)
                    banco_selecionado = Banco.objects.get(id=banco_id)

                    try:
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
                    except Exception as e:
                        erros.append(f"{cliente_obj.razao_social}: erro ao gerar ({e})")

            if contas_geradas:
                self.message_user(request, f"Sucesso! {contas_geradas} Contas a Receber geradas.", messages.SUCCESS)
            for erro in erros:
                self.message_user(request, f"Ignorado — {erro}", messages.WARNING)
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


class BancoPagarFilter(admin.SimpleListFilter):
    title = 'Banco'
    parameter_name = 'banco_pagar'

    def lookups(self, request, model_admin):
        from cadastros.models import Banco
        return list(Banco.objects.values_list('id', 'nome').order_by('nome'))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(banco__id=self.value())


class BancoReceberFilter(admin.SimpleListFilter):
    title = 'Banco'
    parameter_name = 'banco_receber'

    def lookups(self, request, model_admin):
        from cadastros.models import Banco
        return list(Banco.objects.values_list('id', 'nome').order_by('nome'))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(banco__id=self.value())


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


class ResponsavelPagamentoFilter(admin.SimpleListFilter):
    title = 'Responsável pelo Pagamento'
    parameter_name = 'responsavel_pagamento'

    def lookups(self, request, model_admin):
        grupos_permitidos = Group.objects.filter(name__in=['Aprovador Financeiro', 'Operador'])
        usuarios = UsuarioCustomizado.objects.filter(
            groups__in=grupos_permitidos
        ).distinct().order_by('first_name', 'last_name')
        return [(u.id, u.get_full_name() or u.username) for u in usuarios]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(responsavel_pagamento__id=self.value())


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
from django import forms as django_forms

class ContasAPagarForm(django_forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        supervisor = cleaned_data.get('supervisor')
        if status == 'PAGO' and supervisor:
            old_status = None
            if self.instance.pk:
                try:
                    old_status = ContasAPagar.objects.get(pk=self.instance.pk).status
                except ContasAPagar.DoesNotExist:
                    pass
            if old_status != 'PAGO':
                saldo_aberto = SaldoSupervisor.objects.filter(
                    supervisor=supervisor, status='ABERTO'
                ).first()
                if saldo_aberto:
                    nome = supervisor.first_name.strip() or supervisor.username
                    raise django_forms.ValidationError(
                        f"❌ {nome} já possui um ciclo em aberto ({saldo_aberto.numero}). "
                        f"Feche o ciclo atual em Saldo Supervisores antes de registrar novo crédito."
                    )
        return cleaned_data

    class Meta:
        model = ContasAPagar
        fields = '__all__'


class ContasAPagarAdmin(ImportExportModelAdmin):
    resource_classes = [ContasAPagarResource]
    form = ContasAPagarForm
    list_display = ('nota', 'fornecedor', 'vencimento', 'valor', 'status_visual', 'responsavel_pagamento', 'data_baixa', 'usuario_baixa')
    search_fields = ('fornecedor__razao_social', 'nota', 'observacoes')
    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        ('data_baixa', DateRangeFilter),
        EmpresaPagadoraFilter,
        BancoPagarFilter,
        ResponsavelPagamentoFilter,
        NotaSearchFilter,
        FornecedorSearchFilter,
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente, gerar_fixos_mensais]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        grupos_permitidos = Group.objects.filter(name__in=['Aprovador Financeiro', 'Operador'])
        qs = UsuarioCustomizado.objects.filter(groups__in=grupos_permitidos).distinct().order_by('first_name', 'last_name')
        if 'responsavel_pagamento' in form.base_fields:
            form.base_fields['responsavel_pagamento'].queryset = qs
            form.base_fields['responsavel_pagamento'].empty_label = '— Não atribuído —'
        grupo_adm = Group.objects.filter(name='Administrativo').first()
        if grupo_adm and 'supervisor' in form.base_fields:
            form.base_fields['supervisor'].queryset = UsuarioCustomizado.objects.filter(
                groups=grupo_adm
            ).order_by('first_name', 'last_name')
            form.base_fields['supervisor'].empty_label = '— Nenhum —'
        return form

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Sum
        from cadastros.models import Banco
        extra = extra_context or {}
        extra['custom_filter_template'] = 'admin/financeiro/contasapagar/_filters.html'
        extra['empresas_opts'] = list(
            ContasAPagar.objects.select_related('empresa_pagadora')
            .values_list('empresa_pagadora__id', 'empresa_pagadora__nome')
            .distinct().order_by('empresa_pagadora__nome')
        )
        extra['bancos_opts'] = list(Banco.objects.values_list('id', 'nome').order_by('nome'))
        grupos_permitidos = Group.objects.filter(name__in=['Aprovador Financeiro', 'Operador'])
        usuarios = UsuarioCustomizado.objects.filter(
            groups__in=grupos_permitidos
        ).distinct().order_by('first_name', 'last_name')
        extra['responsaveis_opts'] = [
            (u.id, u.first_name.strip() or u.username)
            for u in usuarios
        ]
        response = super().changelist_view(request, extra_context=extra)
        try:
            qs = response.context_data['cl'].queryset
            total = qs.aggregate(t=Sum('valor'))['t'] or 0
            response.context_data['total_filtrado_fmt'] = '{:,.2f}'.format(float(total)).replace(',', 'X').replace('.', ',').replace('X', '.')
        except (AttributeError, KeyError):
            pass
        return response

    def save_model(self, request, obj, form, change):
        if obj.status == 'PAGO' and not obj.usuario_baixa:
            obj.usuario_baixa = request.user
        obj.save(request=request)

    class Media:
        js = ('js/cp_plano_de_contas.js',)


# --- 2. CONTAS A RECEBER ---
class ContasAReceberAdmin(ImportExportModelAdmin):
    resource_classes = [ContasAReceberResource]
    list_display = ('nota', 'cliente', 'vencimento', 'valor', 'status_visual', 'data_baixa', 'usuario_baixa')
    search_fields = ('cliente__razao_social', 'nota', 'observacoes')
    list_filter = (
        StatusFilter,
        ('vencimento', DateRangeFilter),
        ('data_baixa', DateRangeFilter),
        EmpresaPrestadoraFilter,
        BancoReceberFilter,
        NotaSearchFilter,
        ClienteSearchFilter,
    )
    date_hierarchy = 'vencimento'
    readonly_fields = ('data_baixa', 'usuario_baixa')
    exclude = ('nota',)
    actions = [marcar_como_pago, marcar_como_cancelado, marcar_como_pendente]

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Sum
        from cadastros.models import Banco
        extra = extra_context or {}
        extra['custom_filter_template'] = 'admin/financeiro/contasareceber/_filters.html'
        extra['empresas_opts'] = list(
            ContasAReceber.objects.select_related('empresa_prestadora')
            .values_list('empresa_prestadora__id', 'empresa_prestadora__nome')
            .distinct().order_by('empresa_prestadora__nome')
        )
        extra['bancos_opts'] = list(Banco.objects.values_list('id', 'nome').order_by('nome'))
        response = super().changelist_view(request, extra_context=extra)
        try:
            qs = response.context_data['cl'].queryset
            total = qs.aggregate(t=Sum('valor'))['t'] or 0
            response.context_data['total_filtrado_fmt'] = '{:,.2f}'.format(float(total)).replace(',', 'X').replace('.', ',').replace('X', '.')
        except (AttributeError, KeyError):
            pass
        return response

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


# ── Saldo Supervisores ──────────────────────────────────────────────────────

class MovimentacaoInline(admin.TabularInline):
    model = MovimentacaoSupervisor
    extra = 0
    readonly_fields = ('data', 'tipo_display', 'valor_display', 'link_origem', 'wf_data_alteracao', 'wf_observacao')
    fields = ('data', 'tipo_display', 'valor_display', 'link_origem', 'wf_data_alteracao', 'wf_observacao')
    can_delete = False
    ordering = ('-data', '-id')
    verbose_name = "Movimentação"
    verbose_name_plural = "Histórico de Movimentações"

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _get_despesa(self, obj):
        import re
        from workflow.models import Despesa
        despesa_id = obj.referencia_despesa_id
        if not despesa_id:
            match = re.search(r'#(\d+)', obj.descricao or '')
            if match:
                despesa_id = int(match.group(1))
        if despesa_id:
            try:
                return Despesa.objects.get(pk=despesa_id)
            except Despesa.DoesNotExist:
                return None
        return None

    def tipo_display(self, obj):
        if obj.tipo == 'CREDITO':
            return format_html('<span style="color:#27ae60;font-weight:bold;">⬆ Crédito</span>')
        return format_html('<span style="color:#e74c3c;font-weight:bold;">⬇ Débito</span>')
    tipo_display.short_description = "Tipo"

    def valor_display(self, obj):
        cor = '#27ae60' if obj.tipo == 'CREDITO' else '#e74c3c'
        sinal = '+' if obj.tipo == 'CREDITO' else '-'
        return format_html(
            '<span style="color:{};font-weight:bold;">{} R$ {}</span>',
            cor, sinal, f'{obj.valor:,.2f}'
        )
    valor_display.short_description = "Valor"

    def link_origem(self, obj):
        import re
        from django.urls import reverse
        despesa_id = obj.referencia_despesa_id
        if not despesa_id:
            match = re.search(r'#(\d+)', obj.descricao or '')
            if match:
                despesa_id = int(match.group(1))
        if despesa_id:
            url = reverse('admin:workflow_despesa_change', args=[despesa_id])
            return format_html('<a href="{}" target="_blank">WF #{}</a>', url, despesa_id)
        if obj.referencia_cp_id:
            url = reverse('admin:financeiro_contasapagar_change', args=[obj.referencia_cp_id])
            return format_html('<a href="{}" target="_blank">CP {}</a>', url, obj.referencia_cp)
        return '—'
    link_origem.short_description = "ID Origem"

    def wf_data_alteracao(self, obj):
        despesa = self._get_despesa(obj)
        if despesa:
            from workflow.models import LogWorkflow
            log = LogWorkflow.objects.filter(
                despesa=despesa, acao='CONFERIDO'
            ).order_by('-data_hora').first()
            if log:
                return log.data_hora.strftime('%d/%m/%Y %H:%M')
        return '—'
    wf_data_alteracao.short_description = "Conferido em (WF)"

    def wf_observacao(self, obj):
        despesa = self._get_despesa(obj)
        if despesa and despesa.observacoes:
            return despesa.observacoes
        return '—'
    wf_observacao.short_description = "Observação (WF)"


class SaldoSupervisorAdmin(admin.ModelAdmin):
    change_form_template = 'admin/financeiro/saldosupervisor/change_form.html'
    change_list_template = 'admin/financeiro/saldosupervisor/change_list.html'
    list_display = ('numero', 'nome_supervisor', 'data_inicio', 'saldo_disponivel_display', 'utilizacao_display', 'saldo_display', 'status_display')
    list_filter = ('status',)
    readonly_fields = ('numero', 'supervisor', 'saldo_disponivel', 'data_inicio', 'status', 'fechado_por', 'data_fechamento', 'saldo_disponivel_display', 'utilizacao_display', 'saldo_display')
    fields = ('numero', 'supervisor', 'saldo_disponivel_display', 'utilizacao_display', 'saldo_display', 'data_inicio', 'status', 'fechado_por', 'data_fechamento')
    inlines = [MovimentacaoInline]
    actions = ['fechar_ciclo']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        numero = request.GET.get('ss_numero', '').strip()
        supervisor = request.GET.get('ss_supervisor', '').strip()
        inicio_de = request.GET.get('ss_inicio_de', '').strip()
        inicio_ate = request.GET.get('ss_inicio_ate', '').strip()
        status = request.GET.get('ss_status', '').strip()
        if numero:
            qs = qs.filter(numero__icontains=numero)
        if supervisor:
            qs = qs.filter(supervisor__first_name__icontains=supervisor)
        if inicio_de:
            qs = qs.filter(data_inicio__gte=inicio_de)
        if inicio_ate:
            qs = qs.filter(data_inicio__lte=inicio_ate)
        if status:
            qs = qs.filter(status=status)
        return qs

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and '_fechar_ciclo_btn' in request.POST and object_id:
            from django.utils import timezone as tz
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            obj = self.get_object(request, object_id)
            if obj and obj.status == 'ABERTO':
                obj.status = 'FECHADO'
                obj.fechado_por = request.user
                obj.data_fechamento = tz.now()
                obj.observacao_fechamento = request.POST.get('observacao_fechamento', '').strip()
                obj.save()
                self.message_user(request, f"Ciclo {obj.numero} fechado com sucesso.")
                return HttpResponseRedirect(reverse('admin:financeiro_saldosupervisor_changelist'))
        return super().changeform_view(request, object_id, form_url, extra_context)

    def fechar_ciclo(self, request, queryset):
        from django.utils import timezone as tz
        fechados = 0
        for saldo in queryset.filter(status='ABERTO'):
            saldo.status = 'FECHADO'
            saldo.fechado_por = request.user
            saldo.data_fechamento = tz.now()
            saldo.save()
            fechados += 1
        self.message_user(request, f"{fechados} linha(s) fechada(s) com sucesso.")
    fechar_ciclo.short_description = "Fechar ciclo selecionado"

    def status_display(self, obj):
        if obj.status == 'ABERTO':
            return format_html('<span style="background:#f1c40f;color:#000;padding:3px 10px;border-radius:4px;font-weight:bold;">Aberto</span>')
        return format_html('<span style="background:#27ae60;color:#fff;padding:3px 10px;border-radius:4px;font-weight:bold;">Fechado</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'

    def nome_supervisor(self, obj):
        nome = obj.supervisor.first_name.strip() if obj.supervisor.first_name else ''
        return nome or obj.supervisor.username
    nome_supervisor.short_description = "Supervisor"

    def saldo_disponivel_display(self, obj):
        return format_html('<span style="color:#27ae60;font-weight:bold;">R$ {}</span>', f'{obj.saldo_disponivel:,.2f}')
    saldo_disponivel_display.short_description = "Saldo Disponível"

    def utilizacao_display(self, obj):
        return format_html('<span style="color:#e74c3c;font-weight:bold;">R$ {}</span>', f'{obj.utilizacao:,.2f}')
    utilizacao_display.short_description = "Utilização"

    def saldo_display(self, obj):
        saldo = obj.saldo
        cor = '#27ae60' if saldo >= 0 else '#e74c3c'
        return format_html('<span style="color:{};font-weight:bold;">R$ {}</span>', cor, f'{saldo:,.2f}')
    saldo_display.short_description = "Saldo"


# --- REGISTROS FINAIS ---
admin.site.register(ContasAPagar, ContasAPagarAdmin)
admin.site.register(ContasAReceber, ContasAReceberAdmin)
admin.site.register(BaseSaldo, BaseSaldoAdmin)
admin.site.register(Transferencia, TransferenciaAdmin)
admin.site.register(SaldoSupervisor, SaldoSupervisorAdmin)