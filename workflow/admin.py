# workflow/admin.py

from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django import forms
from django.utils import timezone
from django.contrib.auth.models import Group

from .models import Despesa, LogWorkflow
from financeiro.models import ContasAPagar
from core.models import UsuarioCustomizado


# --- 1. FORMULÁRIO COM CAMPO OCULTO DE SEGURANÇA ---
class DespesaForm(forms.ModelForm):
    # Campo invisível para garantir que o tipo nunca se perca
    tipo_reserva = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Despesa
        fields = '__all__'
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # 1. TIPO REAL E CAMPO OCULTO
        tipo_real = None
        if self.instance.pk:
            tipo_real = self.instance.tipo_lancamento
        elif self.request and self.request.GET.get('tipo'):
            tipo_real = self.request.GET.get('tipo')

        if tipo_real:
            self.fields['tipo_reserva'].initial = tipo_real
            self.instance.tipo_lancamento = tipo_real

        # 2. FILTRO DE OPERADORES
        if 'operador' in self.fields:
            try:
                grupo_op = Group.objects.get(name='Operador')
                self.fields['operador'].queryset = UsuarioCustomizado.objects.filter(groups=grupo_op)
            except Group.DoesNotExist:
                pass

        # --- 3. FILTRO DE STATUS COM DEBUG (AQUI ESTÁ A MUDANÇA) ---
        if self.request and 'status' in self.fields:
            user = self.request.user

            # IMPRIME NO TERMINAL PARA GENTE VER O QUE ESTÁ ACONTECENDO
            print(f"--- DEBUG PERMISSÕES ---")
            print(f"Usuário: {user.username}")
            print(f"É Superuser? {user.is_superuser}")

            if not user.is_superuser:
                # Pega os grupos
                grupos_usuario = list(user.groups.values_list('name', flat=True))
                print(f"Grupos Encontrados: {grupos_usuario}")  # <--- OLHE ISSO NO TERMINAL

                status_atual = self.instance.status if self.instance.pk else 'AGUARDANDO_RH'

                # REGRAS EXATAS (Verifique se o nome aqui bate com o print do terminal)
                regras_acesso = {
                    'Aprovador RH': ['AGUARDANDO_RH', 'AGUARDANDO_FIN', 'CANCELADO'],
                    'Aprovador Financeiro': ['AGUARDANDO_FIN', 'DIRECIONADO_OP', 'PAGO', 'CANCELADO'],
                    'Operador': ['DIRECIONADO_OP', 'PAGO', 'CANCELADO'],
                    'Solicitante': []
                }

                status_permitidos = set()
                status_permitidos.add(status_atual)  # Sempre mantém o atual

                match_encontrado = False
                for grupo in grupos_usuario:
                    if grupo in regras_acesso:
                        print(f"Aplicando regra do grupo: {grupo}")
                        status_permitidos.update(regras_acesso[grupo])
                        match_encontrado = True

                if not match_encontrado:
                    print("Nenhum grupo bateu com as regras. Mantendo apenas status atual.")

                # Aplica o filtro
                todas_opcoes = list(self.fields['status'].choices)
                self.fields['status'].choices = [
                    (k, v) for k, v in todas_opcoes if k in status_permitidos
                ]
            else:
                print("Usuário é Superuser: Vê tudo.")
        # -----------------------------------------------------------

        # 4. REMOVE TRAVAMENTOS HTML
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

        # Resgate de Readonly
        if self.instance.pk:
            protegidos = ['data_despesa', 'fornecedor', 'valor', 'solicitante', 'observacoes']
            for campo in protegidos:
                if not cleaned_data.get(campo):
                    original = getattr(self.instance, campo)
                    if original:
                        cleaned_data[campo] = original
                        if campo in self._errors: del self._errors[campo]

        # Validações
        status = cleaned_data.get('status')
        operador = cleaned_data.get('operador')

        if status == 'DIRECIONADO_OP' and not operador:
            self.add_error('operador', 'Selecione um Operador para direcionar.')

        if tipo == 'SOLICITACAO':
            if 'comprovante' in self._errors: del self._errors['comprovante']
            if not self.instance.pk:
                obrig_solic = ['inicio_cobertura', 'fim_cobertura', 'tomador', 'filial',
                               'motivo_ausencia', 'colaborador_faltou', 'forma_pagamento', 'dados_bancarios_pagto']
                for c in obrig_solic:
                    if not cleaned_data.get(c): self.add_error(c, 'Obrigatório na Solicitação.')

        elif tipo == 'CAIXINHA':
            limpar = ['inicio_cobertura', 'fim_cobertura', 'tomador', 'filial',
                      'motivo_ausencia', 'colaborador_faltou', 'nome_cobriu',
                      'forma_pagamento', 'dados_bancarios_pagto']
            for c in limpar:
                if c in self._errors: del self._errors[c]
            if not self.instance.pk and not cleaned_data.get('comprovante'):
                self.add_error('comprovante', 'Obrigatório.')

        motivo = cleaned_data.get('motivo_cancelamento')
        if status and 'CANCELADO' in str(status) and not motivo:
            self.add_error('motivo_cancelamento', 'Motivo obrigatório ao cancelar.')

        if self.errors:
            msg = " | ".join(
                [f"{self.fields.get(k, k).label if k in self.fields else k}: {v[0]}" for k, v in self.errors.items()])
            raise ValidationError(f"ERRO: {msg}")

        return cleaned_data


class LogInline(admin.TabularInline):
    model = LogWorkflow
    readonly_fields = ('usuario', 'perfil_usuario', 'acao', 'data_hora', 'observacao')
    extra = 0
    can_delete = False
    verbose_name = "Histórico"
    verbose_name_plural = "Histórico"


# --- ADMIN PRINCIPAL ---
class DespesaAdmin(admin.ModelAdmin):
    # AQUI ESTAVA O ERRO: Precisamos declarar o form aqui para o get_fieldsets reconhecer o campo oculto
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
        'AGUARDANDO_RH': '#f39c12', 'AGUARDANDO_FIN': '#3498db',
        'DIRECIONADO_OP': '#9b59b6', 'PAGO': '#27ae60',
        'RASCUNHO': '#95a5a6', 'CANCELADO': '#c0392b'
    }

    # INJEÇÃO DO REQUEST
    def get_form(self, request, obj=None, **kwargs):
        # Captura a classe de formulário gerada pelo Django (que herda de DespesaForm)
        FormClass = super().get_form(request, obj, **kwargs)

        # Cria uma subclasse dinâmica para injetar o request no __init__
        class RequestDespesaForm(FormClass):
            def __init__(self, *args, **kwargs):
                kwargs['request'] = request
                super().__init__(*args, **kwargs)

        return RequestDespesaForm

    # --- SAVE ---
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.solicitante = request.user
            # Pega o tipo do form limpo (que veio do campo oculto)
            if form.cleaned_data.get('tipo_lancamento'):
                obj.tipo_lancamento = form.cleaned_data['tipo_lancamento']

            if obj.tipo_lancamento == 'SOLICITACAO':
                obj.status = 'AGUARDANDO_RH'
            else:
                obj.status = 'AGUARDANDO_FIN'
            acao_log = "Criou Registro"
        else:
            acao_log = "Editou"

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

        obs = f"Status: {obj.get_status_display()}"
        if obj.operador: obs += f" -> {obj.operador.first_name}"

        LogWorkflow.objects.create(despesa=obj, usuario=request.user, perfil_usuario=perfil, acao=acao_log,
                                   observacao=obs)

    # --- VISUAL E PERMISSÕES ---
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        tipo = request.GET.get('tipo')
        if tipo in ['CAIXINHA', 'SOLICITACAO']: initial['tipo_lancamento'] = tipo
        return initial

    def get_readonly_fields(self, request, obj=None):
        # --- CORREÇÃO DO ERRO KEYERROR ---
        # Removi 'tipo_reserva' desta lista. Ele deve continuar ativo (oculto) para funcionar.
        ro_fields = ['tipo_lancamento', 'solicitante', 'data_ultima_alteracao']

        # SE ESTIVER EDITANDO (Despesa já criada)
        if obj:
            # 1. Bloqueia TODOS os campos preenchidos pelo Solicitante original
            campos_originais = [
                # Dados Básicos
                'data_despesa', 'fornecedor', 'valor', 'observacoes',
                # Caixinha
                'comprovante',
                # Solicitação
                'inicio_cobertura', 'fim_cobertura', 'tomador', 'filial',
                'motivo_ausencia', 'colaborador_faltou', 'nome_cobriu',
                'forma_pagamento', 'dados_bancarios_pagto'
            ]
            ro_fields.extend(campos_originais)

            # 2. Verifica quem está acessando para liberar ou travar campos de aprovação
            user = request.user
            grupos = list(user.groups.values_list('name', flat=True))

            # Se for Superusuário, libera tudo (retorna lista vazia ou apenas os de sistema)
            if user.is_superuser:
                return []

                # Se NÃO for Financeiro nem Operador (ex: RH ou Solicitante),
            # trava também os campos de pagamento/execução
            if not ('Aprovador Financeiro' in grupos or 'Operador' in grupos):
                ro_fields.extend(['empresa_pagadora', 'banco_pagador', 'operador'])

        return ro_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Dados do Lançamento', {
                'fields': (
                    'tipo_lancamento', 'tipo_reserva',  # Campo oculto incluído aqui
                    'fornecedor', 'data_despesa', 'valor', 'observacoes',
                    'comprovante',
                    ('inicio_cobertura', 'fim_cobertura'),
                    ('tomador', 'filial'),
                    ('motivo_ausencia', 'colaborador_faltou'),
                    'nome_cobriu',
                    ('forma_pagamento', 'dados_bancarios_pagto')
                )
            }),
        ]
        user = request.user
        grupos = list(user.groups.values_list('name', flat=True))
        is_aprovador = any(g in grupos for g in ['Aprovador Financeiro', 'Aprovador RH', 'Operador'])
        if user.is_superuser or is_aprovador:
            fieldsets.append(('Aprovação / Execução', {
                'fields': ('status', 'operador', 'empresa_pagadora', 'banco_pagador', 'motivo_cancelamento')}))
        return fieldsets

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser: return qs
        grupos = list(user.groups.values_list('name', flat=True))
        if 'Aprovador Financeiro' in grupos or 'Operador' in grupos: return qs
        if 'Aprovador RH' in grupos: return qs.filter(Q(tipo_lancamento='SOLICITACAO') | Q(status='AGUARDANDO_RH'))
        return qs.filter(solicitante=user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "fornecedor":
            user = request.user
            if not user.is_superuser and hasattr(user, 'acesso_despesa') and user.acesso_despesa:
                letras = [l.strip() for l in user.acesso_despesa.split(',')]
                kwargs["queryset"] = db_field.related_model.objects.filter(letra_acesso__in=letras)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
        cor = '#34495e' if obj.tipo_lancamento == 'CAIXINHA' else '#17a2b8'
        style = f'color:white; background-color:{cor}; padding:5px; border-radius:4px; display: inline-block; width: 100px; text-align: center;'
        return mark_safe(f'<span style="{style}">{obj.get_tipo_lancamento_display()}</span>')

    tipo_badge.short_description = "Tipo"

    def botao_detalhes(self, obj):
        return mark_safe(f'<a class="button" href="{obj.id}/change/">🔎 Ver</a>')

    botao_detalhes.short_description = "Ação"


admin.site.register(Despesa, DespesaAdmin)