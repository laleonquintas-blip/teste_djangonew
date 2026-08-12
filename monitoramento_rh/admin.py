from django import forms as django_forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.html import format_html
from django.db import models
from django.db.models import Sum
from .models import CoberturasRH, Folha, ColaboradorInformal, PagamentoFolha, ItemPagamento


def _in_group(user, *names):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=names).exists()


@admin.register(CoberturasRH)
class CoberturasRHAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/admin/monitoramento-rh/coberturas/')

    def has_add_permission(self, request):        return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


# ── Colaboradores Informais inline ────────────────────────────────────────────

class ColaboradorInformalInlineForm(django_forms.ModelForm):
    class Meta:
        model = ColaboradorInformal
        fields = '__all__'
        help_texts = {
            'ativo': 'Desmarque para excluir este colaborador das próximas folhas '
                      '(ex.: saiu/foi desligado) sem apagar o histórico de pagamentos já feitos.',
        }


class ColaboradorInformalInline(admin.TabularInline):
    model   = ColaboradorInformal
    form    = ColaboradorInformalInlineForm
    extra   = 1
    fields  = ('filial', 'qt', 'nome', 'cpf', 'registro', 'banco', 'agencia', 'conta', 'valor_padrao', 'ativo')
    ordering = ('banco', 'nome')
    verbose_name_plural = 'Colaboradores Ativos'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(ativo=True)


class ColaboradorInformalInativoInline(admin.TabularInline):
    model   = ColaboradorInformal
    form    = ColaboradorInformalInlineForm
    extra   = 0
    fields  = ('filial', 'qt', 'nome', 'cpf', 'registro', 'banco', 'agencia', 'conta', 'valor_padrao', 'ativo')
    ordering = ('banco', 'nome')
    verbose_name_plural = 'Colaboradores Inativos (histórico — saíram ou foram desligados)'
    classes = ('collapse',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(ativo=False)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Folha)
class FolhaAdmin(admin.ModelAdmin):
    list_display  = ('id', 'tomador', 'tipo', 'descricao', 'ativa', 'total_colaboradores')
    list_filter   = ('tipo', 'ativa', 'tomador')
    search_fields = ('tomador__nome', 'descricao')
    inlines       = [ColaboradorInformalInline, ColaboradorInformalInativoInline]
    fields        = ('tomador', 'tipo', 'descricao', 'fornecedor', 'empresa_pagadora', 'plano_de_contas', 'ativa')

    def total_colaboradores(self, obj):
        return obj.colaboradores.filter(ativo=True).count()
    total_colaboradores.short_description = 'Colaboradores ativos'

    # Nota: não é preciso checar ItemPagamento manualmente aqui — o Django admin
    # já impede a exclusão de ColaboradorInformal com pagamentos vinculados
    # (colaborador é PROTECT em ItemPagamento) e mostra um erro de validação
    # automaticamente antes de chegar em save_formset. Para excluir alguém que
    # já recebeu algum pagamento, desmarque "Ativo" em vez de excluir.


# ── Itens inline (dentro de PagamentoFolha) ──────────────────────────────────

class ItemPagamentoInline(admin.TabularInline):
    model           = ItemPagamento
    extra           = 0
    fields          = ('colaborador_info', 'filial_info', 'banco_info', 'valor_anterior', 'valor_atual', 'justificativa')
    readonly_fields = ('colaborador_info', 'filial_info', 'banco_info', 'valor_anterior')
    ordering        = ('colaborador__banco', 'colaborador__nome')
    can_delete      = False
    verbose_name_plural = 'Itens da Folha (por banco)'

    def colaborador_info(self, obj):
        return f'{obj.colaborador.nome} — CPF: {obj.colaborador.cpf}'
    colaborador_info.short_description = 'Colaborador'

    def filial_info(self, obj):
        return obj.colaborador.filial
    filial_info.short_description = 'Filial'

    def banco_info(self, obj):
        return f'{obj.colaborador.banco} | Ag: {obj.colaborador.agencia} | Cc: {obj.colaborador.conta}'
    banco_info.short_description = 'Banco / Ag / Conta'

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status not in ('RASCUNHO', 'AGUARDANDO_RH', 'AGUARDANDO_FIN'):
            return self.readonly_fields + ('valor_atual', 'justificativa')
        return self.readonly_fields


@admin.register(PagamentoFolha)
class PagamentoFolhaAdmin(admin.ModelAdmin):
    list_display   = ('id', 'folha', 'data_inicio', 'data_fim', 'status_badge', 'total_fmt', 'link_wf', 'criado_por', 'criado_em')
    list_filter    = ('status', 'folha__tomador', 'folha__tipo')
    search_fields  = ('folha__tomador__nome',)
    inlines        = [ItemPagamentoInline]

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def response_change(self, request, obj):
        # Após salvar inlines: se RASCUNHO e sem pendências, cria WF e avança
        if obj.status == 'RASCUNHO':
            pendentes = self._pendentes_justificativa(obj)
            if pendentes:
                nomes = ', '.join(pendentes)
                self.message_user(
                    request,
                    f'Ainda há justificativas pendentes: {nomes}.',
                    level=messages.ERROR,
                )
                from django.urls import reverse
                url = reverse(
                    f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
                    args=[obj.pk],
                )
                return HttpResponseRedirect(url)
            else:
                self._criar_despesa_wf(request, obj)
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        pendentes = self._pendentes_justificativa(obj)
        if pendentes:
            nomes = ', '.join(pendentes)
            self.message_user(
                request,
                f'Preencha a justificativa para os colaboradores com valor alterado: {nomes}.',
                level=messages.ERROR,
            )
            from django.urls import reverse
            url = reverse(
                f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
                args=[obj.pk],
            )
            return HttpResponseRedirect(url)
        return super().response_add(request, obj, post_url_continue)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return [
                ('Dados do Pagamento', {
                    'fields': ('folha', 'data_inicio', 'data_fim', 'total_folha_preview', 'observacao'),
                }),
                ('Itens da Folha (por banco)', {
                    'fields': ('colaboradores_preview',),
                }),
            ]
        return [
            ('Dados do Pagamento', {
                'fields': ('folha', 'data_inicio', 'data_fim', 'status', 'total', 'observacao'),
            }),
            ('Informações de Auditoria', {
                'fields': ('criado_por', 'criado_em', 'aprovado_rh_por', 'aprovado_rh_em', 'pago_por', 'pago_em'),
                'classes': ('collapse',),
            }),
        ]

    def get_readonly_fields(self, request, obj=None):
        base = ('total', 'criado_por', 'criado_em', 'aprovado_rh_por', 'aprovado_rh_em', 'pago_por', 'pago_em',
                'colaboradores_preview', 'total_folha_preview')
        if obj:
            base += ('status',)
        return base

    def total_folha_preview(self, obj):
        return format_html(
            '<div id="preview-total-folha" style="font-size:1.1rem;font-weight:700;color:#1a6e4a;">—</div>'
        )
    total_folha_preview.short_description = 'Total da Folha'

    def colaboradores_preview(self, obj):
        return format_html(
            '<div id="preview-colaboradores" style="color:#aaa;padding:8px 0;">'
            'Selecione uma folha para ver os colaboradores.</div>'
        )
    colaboradores_preview.short_description = ''

    class Media:
        js = ('js/pagamento_folha_preview.js',)

    def status_badge(self, obj):
        cores = {
            'RASCUNHO':       '#6c757d',
            'ENVIADA':        '#17a2b8',
            'AGUARDANDO_RH':  '#e67e22',
            'AGUARDANDO_FIN': '#8e44ad',
            'PAGA':           '#27ae60',
            'CANCELADA':      '#e74c3c',
        }
        cor = cores.get(obj.status, '#999')
        return format_html('<span style="background:{};color:#fff;padding:3px 8px;border-radius:4px;font-size:.75rem;">{}</span>',
                           cor, obj.get_status_display())
    status_badge.short_description = 'Status'

    def total_fmt(self, obj):
        return f'R$ {obj.total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    total_fmt.short_description = 'Total'

    def link_wf(self, obj):
        try:
            d = obj.despesa_wf
            url = f'/admin/workflow/despesa/{d.id}/change/'
            return format_html('<a href="{}" target="_blank">WF #{}</a>', url, d.id)
        except Exception:
            return '—'
    link_wf.short_description = 'WF'

    def delete_model(self, request, obj):
        from workflow.models import Despesa, LogWorkflow
        try:
            despesa = obj.despesa_wf
            despesa.status = 'CANCELADO'
            despesa.pagamento_folha = None
            despesa.save()
            LogWorkflow.objects.create(
                despesa=despesa,
                usuario=request.user,
                perfil_usuario='Sistema',
                acao='WF cancelado automaticamente — Pagamento de Folha excluído',
            )
        except Exception:
            pass
        super().delete_model(request, obj)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        pendentes = []
        for instance in instances:
            if (instance.valor_anterior is not None
                    and instance.valor_atual != instance.valor_anterior
                    and not instance.justificativa.strip()):
                pendentes.append(instance.colaborador.nome)
        if pendentes:
            nomes = ', '.join(pendentes)
            self.message_user(
                request,
                f'Justificativa obrigatória para colaboradores com valor alterado: {nomes}.',
                level=messages.ERROR,
            )
            return
        for instance in instances:
            instance.save()
        formset.save_m2m()

    def _pendentes_justificativa(self, obj):
        return list(
            obj.itens.filter(valor_anterior__isnull=False, justificativa='')
            .exclude(valor_atual=models.F('valor_anterior'))
            .values_list('colaborador__nome', flat=True)
        )

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        if is_new:
            obj.criado_por = request.user
            obj.status = 'ENVIADA'

        # Bloqueia avanço de status se houver itens sem justificativa
        if change and 'status' in form.changed_data:
            status_anterior = form.initial.get('status', '')
            if status_anterior == 'ENVIADA':
                pendentes = self._pendentes_justificativa(obj)
                if pendentes:
                    nomes = ', '.join(pendentes)
                    self.message_user(
                        request,
                        f'Não é possível avançar o status. Justificativa obrigatória para: {nomes}.',
                        level=messages.ERROR,
                    )
                    obj.status = status_anterior
                    super().save_model(request, obj, form, change)
                    return

        super().save_model(request, obj, form, change)
        self._gerar_ou_atualizar_itens(obj)
        if is_new:
            pendentes = self._pendentes_justificativa(obj)
            if pendentes:
                # Mantém como rascunho e NÃO cria WF até justificativas serem preenchidas
                PagamentoFolha.objects.filter(pk=obj.pk).update(status='RASCUNHO')
                obj.status = 'RASCUNHO'
                nomes = ', '.join(pendentes)
                self.message_user(
                    request,
                    f'Pagamento salvo como RASCUNHO. Justificativa obrigatória para colaboradores com valor alterado: {nomes}. '
                    f'Preencha na aba "Itens da Folha" e salve novamente para enviar para aprovação.',
                    level=messages.ERROR,
                )
            else:
                self._criar_despesa_wf(request, obj)

    def _criar_despesa_wf(self, request, pagamento):
        from workflow.models import Despesa, LogWorkflow
        folha = pagamento.folha

        if _in_group(request.user, 'Aprovador RH'):
            status_inicial = 'AGUARDANDO_FIN'
            perfil = 'RH'
            acao = 'Criou Registro / Aprovado RH automático'
        else:
            status_inicial = 'AGUARDANDO_RH'
            perfil = 'Solicitante'
            acao = 'Criou Registro'

        despesa = Despesa.objects.create(
            tipo_lancamento  = 'FOLHA',
            data_despesa     = pagamento.data_fim,
            valor            = pagamento.total,
            observacoes      = (
                f'Folha: {folha}\n'
                f'Competência: {pagamento.data_inicio} a {pagamento.data_fim}\n'
                f'{pagamento.observacao}'
            ).strip(),
            solicitante      = request.user,
            tomador          = folha.tomador,
            empresa_pagadora = folha.empresa_pagadora,
            status           = status_inicial,
            pagamento_folha  = pagamento,
        )

        LogWorkflow.objects.create(
            despesa        = despesa,
            usuario        = request.user,
            perfil_usuario = perfil,
            acao           = acao,
        )

        pagamento.status = status_inicial
        PagamentoFolha.objects.filter(pk=pagamento.pk).update(status=status_inicial)

    def _gerar_ou_atualizar_itens(self, pagamento):
        for colab in pagamento.folha.colaboradores.filter(ativo=True):
            if not ItemPagamento.objects.filter(pagamento=pagamento, colaborador=colab).exists():
                ultimo = (ItemPagamento.objects
                          .filter(colaborador=colab, pagamento__status='PAGA')
                          .order_by('-pagamento__data_fim')
                          .values_list('valor_atual', flat=True)
                          .first())
                ItemPagamento.objects.create(
                    pagamento=pagamento,
                    colaborador=colab,
                    valor_anterior=ultimo,
                    valor_atual=colab.valor_padrao,
                )
        total = pagamento.itens.aggregate(s=Sum('valor_atual'))['s'] or 0
        PagamentoFolha.objects.filter(pk=pagamento.pk).update(total=total)

