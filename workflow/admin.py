# workflow/admin.py

from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.safestring import mark_safe
from django import forms
from django.utils import timezone
from django.contrib.auth.models import Group

from .models import Despesa, LogWorkflow
from financeiro.models import ContasAPagar
from core.models import UsuarioCustomizado


# --- 1. FORMULÁRIO ---
class DespesaForm(forms.ModelForm):
    tipo_reserva = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Despesa
        fields = '__all__'
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2}),
            'dados_bancarios_pagto': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Campo Oculto de Tipo
        tipo_real = None
        if self.instance.pk:
            tipo_real = self.instance.tipo_lancamento
        elif self.request and self.request.GET.get('tipo'):
            tipo_real = self.request.GET.get('tipo')

        if tipo_real:
            self.fields['tipo_reserva'].initial = tipo_real
            self.instance.tipo_lancamento = tipo_real

        # Filtro de Operadores
        if 'operador' in self.fields:
            try:
                grupo_op = Group.objects.get(name='Operador')
                self.fields['operador'].queryset = UsuarioCustomizado.objects.filter(groups=grupo_op)
            except Group.DoesNotExist:
                pass

        # Filtro de Status Dinâmico
        if self.request and 'status' in self.fields:
            user = self.request.user
            if not user.is_superuser:
                grupos_usuario = list(user.groups.values_list('name', flat=True))

                status_atual = self.instance.status if self.instance.pk else 'AGUARDANDO_RH'
                if tipo_real == 'EXTRA' and not self.instance.pk:
                    status_atual = 'AGUARDANDO_ADM'

                regras_acesso = {
                    'Administrativo': ['AGUARDANDO_ADM', 'AGUARDANDO_RH', 'CANCELADO'],
                    'Aprovador RH': ['AGUARDANDO_RH', 'AGUARDANDO_FIN', 'CANCELADO'],
                    'Aprovador Financeiro': ['AGUARDANDO_FIN', 'DIRECIONADO_OP', 'PAGO', 'CANCELADO'],
                    'Operador': ['DIRECIONADO_OP', 'PAGO', 'CANCELADO'],
                    'Solicitante': []
                }

                status_permitidos = set()
                status_permitidos.add(status_atual)

                for grupo in grupos_usuario:
                    if grupo in regras_acesso:
                        status_permitidos.update(regras_acesso[grupo])

                todas_opcoes = list(self.fields['status'].choices)
                self.fields['status'].choices = [
                    (k, v) for k, v in todas_opcoes if k in status_permitidos
                ]

        # Campos Opcionais
        campos_livres = [
            'data_despesa', 'fornecedor', 'valor', 'observacoes',
            'solicitante', 'status', 'tipo_lancamento', 'operador',
            'comprovante', 'inicio_cobertura', 'fim_cobertura', 'tomador', 'filial',
            'motivo_ausencia', 'colaborador_faltou', 'nome_cobriu',
            'forma_pagamento', 'dados_bancarios_pagto'
        ]
        for campo in campos_livres:
            if campo in self.fields:
                self.fields[campo].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_reserva')
        if not tipo: tipo = self.instance.tipo_lancamento
        if not tipo: tipo = 'CAIXINHA'

        self.instance.tipo_lancamento = tipo
        cleaned_data['tipo_lancamento'] = tipo

        if self.instance.pk:
            protegidos = ['data_despesa', 'fornecedor', 'valor', 'solicitante']

            user = self.request.user if hasattr(self, 'request') else None
            is_admin_group = user and user.groups.filter(name='Administrativo').exists()
            is_extra_inicial = self.instance.tipo_lancamento == 'EXTRA' and self.instance.status == 'AGUARDANDO_ADM'

            if is_extra_inicial and is_admin_group:
                if 'valor' in protegidos: protegidos.remove('valor')

            for campo in protegidos:
                if not cleaned_data.get(campo):
                    original = getattr(self.instance, campo)
                    if original is not None:
                        cleaned_data[campo] = original
                        if campo in self._errors: del self._errors[campo]

        status = cleaned_data.get('status')
        operador = cleaned_data.get('operador')

        if status == 'DIRECIONADO_OP' and not operador:
            self.add_error('operador', 'Selecione um Operador para direcionar.')

        motivo = cleaned_data.get('motivo_cancelamento')
        if status and 'CANCELADO' in str(status) and not motivo:
            self.add_error('motivo_cancelamento', 'Motivo obrigatório ao cancelar.')

        return cleaned_data


class LogInline(admin.TabularInline):
    model = LogWorkflow
    readonly_fields = ('usuario', 'perfil_usuario', 'acao', 'data_hora', 'observacao')
    extra = 0
    can_delete = False
    verbose_name = "Histórico"
    verbose_name_plural = "Histórico"


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    form = DespesaForm
    inlines = [LogInline]

    change_list_template = "admin/workflow/despesa/change_list.html"
    change_form_template = "admin/workflow/despesa/change_form.html"

    class Media:
       js = ('js/admin_despesa.js',)

    list_display = ('id', 'tipo_badge', 'solicitante', 'fornecedor', 'valor_formatado', 'status_badge',
                    'botao_detalhes')
    list_filter = ('tipo_lancamento', 'status', 'fornecedor')
    search_fields = ('id', 'fornecedor__razao_social', 'solicitante__first_name')

    CORES_SISTEMA = {
        'AGUARDANDO_ADM': '#e67e22',
        'AGUARDANDO_RH': '#f39c12', 'AGUARDANDO_FIN': '#3498db',
        'DIRECIONADO_OP': '#9b59b6', 'PAGO': '#27ae60',
        'RASCUNHO': '#95a5a6', 'CANCELADO': '#c0392b'
    }

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class RequestDespesaForm(FormClass):
            def __init__(self, *args, **kwargs):
                kwargs['request'] = request
                super().__init__(*args, **kwargs)

        return RequestDespesaForm

    # --- VISIBILIDADE ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser: return qs
        grupos = list(user.groups.values_list('name', flat=True))

        if 'Aprovador Financeiro' in grupos or 'Operador' in grupos:
            return qs

        filtro_base = Q(solicitante=user)
        if 'Aprovador RH' in grupos: filtro_base |= Q(status='AGUARDANDO_RH')

        return qs.filter(filtro_base).distinct()

    # --- CAMPOS TRAVADOS (READONLY) ---
    def get_readonly_fields(self, request, obj=None):
        ro_fields = ['tipo_lancamento', 'data_ultima_alteracao']

        if obj:
            user = request.user
            grupos = list(user.groups.values_list('name', flat=True))

            if user.is_superuser: return []

            if not self.has_change_permission(request, obj):
                return [f.name for f in self.model._meta.fields]

            # REGRA ADM EXTRA: Trava metadados, mas deixa Valor/Pagto livres
            if obj.tipo_lancamento == 'EXTRA' and obj.status == 'AGUARDANDO_ADM' and 'Administrativo' in grupos:
                # O que o ADM *NÃO* pode mexer:
                ro_fields.extend(['solicitante', 'fornecedor', 'data_despesa', 'observacoes', 'tomador', 'filial'])
                return ro_fields

            # REGRA PADRÃO
            campos_travados_padrao = [
                'solicitante', 'data_despesa', 'fornecedor', 'valor', 'observacoes',
                'comprovante', 'inicio_cobertura', 'fim_cobertura', 'tomador', 'filial',
                'motivo_ausencia', 'colaborador_faltou', 'nome_cobriu',
                'forma_pagamento', 'dados_bancarios_pagto'
            ]
            ro_fields.extend(campos_travados_padrao)

            if not ('Aprovador Financeiro' in grupos or 'Operador' in grupos):
                ro_fields.extend(['empresa_pagadora', 'banco_pagador', 'operador'])

        return ro_fields

    # --- FIELDSETS (LAYOUT CORRIGIDO) ---
    def get_fieldsets(self, request, obj=None):
        # 1. Bloco Principal
        fieldsets = [
            ('Dados do Lançamento', {
                'fields': (
                    'tipo_lancamento', 'tipo_reserva',
                    'solicitante',
                    'fornecedor', 'data_despesa', 'valor', 'observacoes',
                    'comprovante',
                    ('inicio_cobertura', 'fim_cobertura'),
                    ('tomador', 'filial'),
                    ('motivo_ausencia', 'colaborador_faltou')
                )
            }),
        ]

        # 2. Bloco Extra (Pagamento Adm) - AJUSTE AQUI
        # Usamos tuplas individuais (campo,) para forçar uma linha por campo.
        if obj and obj.tipo_lancamento == 'EXTRA':
            fieldsets.append(('Definição de Pagamento (Administrativo)', {
                'fields': (
                    'nome_cobriu',
                    'forma_pagamento',
                    'dados_bancarios_pagto'
                )
            }))

        # 3. Bloco de Aprovação
        user = request.user
        grupos = list(user.groups.values_list('name', flat=True))
        is_aprovador = any(g in grupos for g in ['Aprovador Financeiro', 'Aprovador RH', 'Operador', 'Administrativo'])

        if user.is_superuser or is_aprovador:
            fieldsets.append(('Aprovação / Execução', {
                'fields': ('status', 'operador', 'empresa_pagadora', 'banco_pagador', 'motivo_cancelamento')}))

        return fieldsets

    # --- PERMISSÕES ---
    def has_change_permission(self, request, obj=None):
        if not obj: return True
        user = request.user
        if user.is_superuser: return True

        grupos = list(user.groups.values_list('name', flat=True))

        # Administrativo: Pode editar se for Extra e estiver na fase dele
        if 'Administrativo' in grupos and obj.status == 'AGUARDANDO_ADM':
            if obj.solicitante == user: return True

        if 'Aprovador RH' in grupos and obj.status == 'AGUARDANDO_RH': return True

        if 'Aprovador Financeiro' in grupos:
            if obj.status in ['AGUARDANDO_FIN', 'DIRECIONADO_OP']: return True

        if 'Operador' in grupos:
            if obj.status == 'DIRECIONADO_OP': return True

        if obj.solicitante == user and obj.status == 'RASCUNHO': return True

        return False

    # --- HELPERS ---
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "fornecedor":
            user = request.user
            if not user.is_superuser and hasattr(user, 'acesso_despesa') and user.acesso_despesa:
                letras = [l.strip() for l in user.acesso_despesa.split(',')]
                kwargs["queryset"] = db_field.related_model.objects.filter(letra_acesso__in=letras)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.solicitante = request.user
            if form.cleaned_data.get('tipo_lancamento'):
                obj.tipo_lancamento = form.cleaned_data['tipo_lancamento']

            if obj.tipo_lancamento == 'EXTRA':
                obj.status = 'AGUARDANDO_ADM'
            elif obj.tipo_lancamento == 'SOLICITACAO':
                obj.status = 'AGUARDANDO_RH'
            else:
                obj.status = 'AGUARDANDO_FIN'
            acao_log = "Criou Registro"
        else:
            acao_log = "Editou"
            if obj.tipo_lancamento == 'EXTRA' and obj.status == 'CANCELADO':
                if request.user.groups.filter(name='Aprovador Financeiro').exists():
                    try:
                        if hasattr(obj, 'lancamentoextra'):
                            extra_origem = obj.lancamentoextra
                            if extra_origem.conta_receber_criada:
                                extra_origem.conta_receber_criada.delete()
                                self.message_user(request, "CR vinculado excluído!", level='WARNING')
                                acao_log = "CANCELOU (CR Excluído)"
                    except Exception as e:
                        print(f"Erro: {e}")

        if change and obj.status == 'PAGO' and 'status' in form.changed_data:
            self.gerar_contas_a_pagar(obj, request)
            acao_log = "FINALIZOU (PAGO)"

        super().save_model(request, obj, form, change)

        grupos = list(request.user.groups.values_list('name', flat=True))
        perfil = "Solicitante"
        if request.user.is_superuser:
            perfil = "Admin"
        elif 'Aprovador Financeiro' in grupos:
            perfil = "Financeiro"
        elif 'Aprovador RH' in grupos:
            perfil = "RH"
        elif 'Administrativo' in grupos:
            perfil = "Administrativo"

        obs = f"Status: {obj.get_status_display()}"
        if obj.operador: obs += f" -> {obj.operador.first_name}"
        if 'valor' in form.changed_data: obs += f" | Alterou Valor para R$ {obj.valor}"

        LogWorkflow.objects.create(despesa=obj, usuario=request.user, perfil_usuario=perfil, acao=acao_log,
                                   observacao=obs)

    def gerar_contas_a_pagar(self, despesa, request):
        if not ContasAPagar.objects.filter(nota=f"WF-{despesa.id}").exists():
            ContasAPagar.objects.create(
                fornecedor=despesa.fornecedor, empresa_pagadora=despesa.empresa_pagadora,
                banco=despesa.banco_pagador, data_emissao=despesa.data_despesa,
                vencimento=timezone.now().date(), valor=despesa.valor,
                nota=f"WF-{despesa.id}", status='PAGO',
                data_baixa=timezone.now().date(), usuario_baixa=request.user
            )

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            qs = Despesa.objects.none()
        metrics = qs.order_by().values('status').annotate(total_valor=Sum('valor'), total_qtd=Count('id'))
        summary = []
        for item in metrics:
            st = item['status']
            cor = self.CORES_SISTEMA.get(st, '#95a5a6')
            if 'CANCELADO' in st: cor = self.CORES_SISTEMA['CANCELADO']
            summary.append({
                'status_key': st, 'status_label': dict(Despesa._meta.get_field('status').choices).get(st, st),
                'total_valor': item['total_valor'], 'total_qtd': item['total_qtd'], 'color': cor
            })
        response.context_data['summary_data'] = summary
        return response

    def valor_formatado(self, obj):
        return f"R$ {obj.valor}"

    valor_formatado.short_description = "Valor"

    def status_badge(self, obj):
        cor = self.CORES_SISTEMA.get(obj.status, '#95a5a6')
        if 'CANCELADO' in obj.status: cor = self.CORES_SISTEMA['CANCELADO']
        style = f'color:white; background-color:{cor}; padding:5px; border-radius:10px; font-weight:bold; font-size:11px; display: inline-block; width: 140px; text-align: center;'
        return mark_safe(f'<span style="{style}">{obj.get_status_display()}</span>')

    status_badge.short_description = "Status"

    def tipo_badge(self, obj):
        if obj.tipo_lancamento == 'CAIXINHA':
            cor = '#34495e'
        elif obj.tipo_lancamento == 'EXTRA':
            cor = '#e67e22'
        else:
            cor = '#17a2b8'
        style = f'color:white; background-color:{cor}; padding:5px; border-radius:4px; display: inline-block; width: 100px; text-align: center;'
        return mark_safe(f'<span style="{style}">{obj.get_tipo_lancamento_display()}</span>')

    tipo_badge.short_description = "Tipo"

    def botao_detalhes(self, obj):
        return mark_safe(f'<a class="button" href="{obj.id}/change/">🔎 Ver</a>')

    botao_detalhes.short_description = "Ação"