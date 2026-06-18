# workflow/admin.py

from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.safestring import mark_safe
from django import forms
from django.utils import timezone
from django.contrib.auth.models import Group
import io, zipfile, os, mimetypes
from django.http import HttpResponse
from django.conf import settings
import cloudinary
import cloudinary.uploader
import urllib.request

from rangefilter.filters import DateRangeFilterBuilder

from .models import Despesa, LogWorkflow, STATUS_WORKFLOW
from financeiro.models import ContasAPagar
from core.models import UsuarioCustomizado


# Filtros de texto ocultos para a barra de pesquisa customizada
class _WfTextFilter(admin.SimpleListFilter):
    def lookups(self, request, model_admin): return ()
    def choices(self, changelist): return []
    def has_output(self): return True
    def queryset(self, request, queryset): return queryset


class WfIdFilter(_WfTextFilter):
    title = 'ID'; parameter_name = 'id_q'
    def queryset(self, request, queryset):
        if self.value():
            try: return queryset.filter(id=int(self.value()))
            except ValueError: return queryset.none()


class WfSolicitanteFilter(_WfTextFilter):
    title = 'Solicitante'; parameter_name = 'sol_q'
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                solicitante__first_name__icontains=self.value()
            ) | queryset.filter(
                solicitante__last_name__icontains=self.value()
            ) | queryset.filter(
                solicitante__username__icontains=self.value()
            )


class WfDespesaFilter(_WfTextFilter):
    title = 'Despesa'; parameter_name = 'desp_q'
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(fornecedor__razao_social__icontains=self.value())


# ---------------------------------------------------------------------------
# Mapa de ações por perfil/status → escolhas amigáveis no select de status
# ---------------------------------------------------------------------------
def _build_action_choices(grupos, status_atual, tipo_lancamento=None):
    """
    Retorna as choices do campo status de acordo com o perfil do usuário
    e o status atual do registro.  A primeira opção é sempre "sem ação"
    (mantém o status atual), forçando o usuário a escolher explicitamente
    uma ação.
    """
    from .models import STATUS_WORKFLOW
    labels = dict(STATUS_WORKFLOW)

    # Placeholder: força o usuário a escolher explicitamente uma ação.
    # Se salvar sem trocar, o clean() preserva o status atual.
    sem_acao = ('', '— Selecione uma ação —')

    # ── Sem registro (tela de criação): status auto-definido em save_model
    if not status_atual:
        return [('', '(definido automaticamente)')]

    # ── Comercial ─────────────────────────────────────────────────────────
    if 'Comercial' in grupos and status_atual == 'AGUARDANDO_COMERCIAL':
        return [
            sem_acao,
            ('AGUARDANDO_FIN', '✅ Aprovar'),
            ('CANCELADO',      '❌ Cancelar'),
        ]

    # ── Administrativo ────────────────────────────────────────────────────
    if 'Administrativo' in grupos and status_atual == 'AGUARDANDO_ADM':
        # Caixinhas vão direto ao Financeiro; Solicitações/Extras passam pelo RH
        proximo       = 'AGUARDANDO_FIN' if tipo_lancamento == 'CAIXINHA' else 'AGUARDANDO_RH'
        label_aprovar = '✅ Reenviar ao Financeiro' if tipo_lancamento == 'CAIXINHA' else '✅ Aprovar'
        return [
            sem_acao,
            (proximo,  label_aprovar),
            ('CANCELADO', '❌ Cancelar'),
        ]

    # ── Comercial (caixinha devolvida pelo Financeiro) ─────────────────────
    if 'Comercial' in grupos and status_atual == 'AGUARDANDO_ADM':
        return [
            sem_acao,
            ('AGUARDANDO_FIN', '✅ Reenviar ao Financeiro'),
            ('CANCELADO',      '❌ Cancelar'),
        ]

    # ── Aprovador RH ──────────────────────────────────────────────────────
    if 'Aprovador RH' in grupos and status_atual == 'AGUARDANDO_RH':
        return [
            sem_acao,
            ('AGUARDANDO_FIN', '✅ Aprovar'),
            ('AGUARDANDO_ADM', '↩ Retornar ao Administrativo'),
            ('CANCELADO',      '❌ Cancelar'),
        ]

    # ── Aprovador Financeiro ───────────────────────────────────────────────
    if 'Aprovador Financeiro' in grupos:
        # Caixinha não passa pelo RH: devolução vai ao solicitante (AGUARDANDO_ADM)
        destino_devolucao_fin = 'AGUARDANDO_ADM' if tipo_lancamento == 'CAIXINHA' else 'AGUARDANDO_RH'
        label_devolucao_fin   = '↩ Devolver ao Solicitante' if tipo_lancamento == 'CAIXINHA' else '↩ Devolver ao RH'

        # De DIRECIONADO_OP, desfaz o direcionamento retornando à própria fila do Financeiro
        # (ou ao solicitante no caso de caixinha)
        destino_devolucao_op = 'AGUARDANDO_ADM' if tipo_lancamento == 'CAIXINHA' else 'AGUARDANDO_FIN'
        label_devolucao_op   = '↩ Devolver ao Solicitante' if tipo_lancamento == 'CAIXINHA' else '↩ Cancelar Direcionamento'

        status_final = 'CONFERIDO' if tipo_lancamento == 'CAIXINHA' else 'PAGO'
        label_final  = '✅ Conferido' if tipo_lancamento == 'CAIXINHA' else '✅ Marcar como Pago'

        if status_atual == 'AGUARDANDO_FIN':
            return [
                sem_acao,
                ('DIRECIONADO_OP',      'Direcionar ao Operador'),
                (status_final,          label_final),
                (destino_devolucao_fin, label_devolucao_fin),
                ('CANCELADO',           '❌ Cancelar'),
            ]
        if status_atual == 'DIRECIONADO_OP':
            return [
                sem_acao,
                (status_final,         label_final),
                (destino_devolucao_op, label_devolucao_op),
                ('CANCELADO',          '❌ Cancelar'),
            ]

    # ── Operador ──────────────────────────────────────────────────────────
    if 'Operador' in grupos and status_atual == 'DIRECIONADO_OP':
        return [
            sem_acao,
            ('PAGO',           '✅ Marcar como Pago'),
            ('AGUARDANDO_FIN', '↩ Devolver ao Financeiro'),
            ('CANCELADO',      '❌ Cancelar'),
        ]

    # Fallback: somente visualização
    return [(status_atual, labels.get(status_atual, status_atual))]


# --- 1. FORMULÁRIO ---
class DespesaForm(forms.ModelForm):
    tipo_reserva = forms.CharField(widget=forms.HiddenInput(), required=False)
    mensagem = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Adicione uma mensagem ou resposta (opcional)…'}),
        required=False,
        label='Mensagem / Resposta',
        help_text='Esta mensagem ficará registrada no histórico de diálogo.'
    )

    class Meta:
        model = Despesa
        fields = '__all__'
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2}),
            'dados_bancarios_pagto': forms.Textarea(attrs={'rows': 3}),
            'justificativa_retorno': forms.Textarea(attrs={'rows': 3}),
            'motivo_cancelamento': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk and self.request:
            self.fields['solicitante'].initial = self.request.user
            self.fields['solicitante'].disabled = True
            self.fields['solicitante'].help_text = "Definido automaticamente como o usuário logado."

        tipo_real = None
        if self.instance.pk:
            tipo_real = self.instance.tipo_lancamento
        elif self.request and self.request.GET.get('tipo'):
            tipo_real = self.request.GET.get('tipo')

        if tipo_real:
            self.fields['tipo_reserva'].initial = tipo_real
            self.instance.tipo_lancamento = tipo_real

        if 'operador' in self.fields:
            try:
                grupo_op = Group.objects.get(name='Operador')
                self.fields['operador'].queryset = UsuarioCustomizado.objects.filter(groups=grupo_op)
            except Group.DoesNotExist:
                pass

        if self.request and 'status' in self.fields:
            user = self.request.user
            if not user.is_superuser:
                grupos_usuario = list(user.groups.values_list('name', flat=True))

                if self.instance.pk:
                    status_atual = self.instance.status
                    self.fields['status'].choices = _build_action_choices(
                        grupos_usuario,
                        status_atual,
                        tipo_lancamento=self.instance.tipo_lancamento,
                    )
                else:
                    # Novo registro: status definido automaticamente em save_model
                    pass

        campos_livres = [
            'data_despesa', 'fornecedor', 'valor', 'observacoes',
            'solicitante', 'status', 'tipo_lancamento', 'operador',
            'comprovante', 'inicio_cobertura', 'fim_cobertura', 'dias_cobertura',
            'tomador', 'filial', 'motivo_ausencia', 'colaborador_faltou',
            'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto'
        ]
        for campo in campos_livres:
            if campo in self.fields:
                self.fields[campo].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_reserva')
        if not tipo:
            tipo = self.instance.tipo_lancamento
        if not tipo:
            tipo = 'CAIXINHA'

        self.instance.tipo_lancamento = tipo
        cleaned_data['tipo_lancamento'] = tipo

        if not self.instance.pk and self.request:
            cleaned_data['solicitante'] = self.request.user
            self.instance.solicitante = self.request.user
            if not cleaned_data.get('valor'):
                self.add_error('valor', 'Este campo é obrigatório.')

        if self.instance.pk:
            protegidos = [
                'data_despesa', 'fornecedor', 'valor', 'solicitante',
                'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto'
            ]

            user = self.request.user if hasattr(self, 'request') else None
            is_admin_group = user and user.groups.filter(name='Administrativo').exists()
            is_rh_group = user and user.groups.filter(name='Aprovador RH').exists()
            is_extra = self.instance.tipo_lancamento == 'EXTRA'

            if is_extra and is_admin_group and self.instance.status == 'AGUARDANDO_ADM':
                campos_editaveis_adm = ['valor', 'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto']
                for c in campos_editaveis_adm:
                    if c in protegidos:
                        protegidos.remove(c)

            if is_extra and is_rh_group and self.instance.status == 'AGUARDANDO_RH':
                campos_editaveis_rh = ['valor', 'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto']
                for c in campos_editaveis_rh:
                    if c in protegidos:
                        protegidos.remove(c)

            for campo in protegidos:
                if not cleaned_data.get(campo):
                    original = getattr(self.instance, campo)
                    if original is not None and original != '':
                        cleaned_data[campo] = original
                        if campo in self._errors:
                            del self._errors[campo]

        status = cleaned_data.get('status')

        # Se nenhuma ação foi selecionada (placeholder ''), preserva o status atual
        if not status and self.instance.pk:
            cleaned_data['status'] = self.instance.status
            status = self.instance.status

        operador = cleaned_data.get('operador')

        if status == 'DIRECIONADO_OP' and not operador:
            self.add_error('operador', 'Selecione um Operador para direcionar.')

        motivo = cleaned_data.get('motivo_cancelamento')
        if status and 'CANCELADO' in str(status) and not motivo:
            self.add_error('motivo_cancelamento', 'Motivo obrigatório ao cancelar.')

        # Justificativa obrigatória em devoluções/retornos
        if self.instance.pk:
            status_anterior = self.instance.status
            tipo = self.instance.tipo_lancamento

            # Qualquer transição "para trás" no fluxo exige justificativa
            RETORNOS = {
                'AGUARDANDO_RH':  {'AGUARDANDO_ADM'},
                'AGUARDANDO_FIN': {'AGUARDANDO_ADM', 'AGUARDANDO_RH'},
                'DIRECIONADO_OP': {'AGUARDANDO_ADM', 'AGUARDANDO_FIN'},
            }
            if status in RETORNOS.get(status_anterior, set()):
                if not cleaned_data.get('justificativa_retorno'):
                    self.add_error('justificativa_retorno',
                                   'Justificativa obrigatória ao retornar/devolver.')

        # VALIDAÇÃO: bloqueia PAGO (não-caixinha) sem empresa e banco
        if status == 'PAGO':
            empresa = cleaned_data.get('empresa_pagadora')
            banco = cleaned_data.get('banco_pagador')
            if not empresa:
                self.add_error('empresa_pagadora', 'Empresa Pagadora é obrigatória para marcar como PAGO.')
            if not banco:
                self.add_error('banco_pagador', 'Banco Pagador é obrigatório para marcar como PAGO.')

        return cleaned_data


class LogInline(admin.TabularInline):
    model = LogWorkflow
    readonly_fields = ('usuario', 'perfil_usuario', 'acao', 'data_hora', 'observacao')
    extra = 0
    can_delete = False
    verbose_name = "Entrada"
    verbose_name_plural = "Log de Ações (interno)"
    # Oculto — o diálogo visual substitui esta tabela no change_form
    classes = ['collapse']


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    form = DespesaForm
    inlines = [LogInline]

    change_list_template = "admin/workflow/despesa/change_list.html"
    change_form_template = "admin/workflow/despesa/change_form.html"

    class Media:
        js = ('js/admin_despesa.js', 'js/dias_cobertura_widget.js')
        css = {
            'all': ('css/admin_fixes.css',)
        }

    actions = ['baixar_e_limpar_comprovantes']

    def baixar_e_limpar_comprovantes(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Acesso negado: apenas superusuários podem executar esta ação.", level='error')
            return

        cfg = settings.CLOUDINARY_STORAGE
        cloudinary.config(
            cloud_name=cfg['CLOUD_NAME'],
            api_key=cfg['API_KEY'],
            api_secret=cfg['API_SECRET'],
        )

        com_comprovante = queryset.exclude(comprovante='').exclude(comprovante__isnull=True)
        if not com_comprovante.exists():
            self.message_user(request, "Nenhuma das ocorrências selecionadas possui comprovante.", level='warning')
            return

        buffer = io.BytesIO()
        total, erros = 0, 0

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for despesa in com_comprovante:
                try:
                    url = despesa.comprovante.url
                    with urllib.request.urlopen(url) as resp:
                        data = resp.read()
                        content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()
                        ext = mimetypes.guess_extension(content_type) or ''
                        ext = {'.jpe': '.jpg', '.jpeg': '.jpg'}.get(ext, ext)
                    if not ext:
                        _, ext = os.path.splitext(despesa.comprovante.name)
                    ext = ext.lstrip('.').lower() or 'bin'
                    nome_arquivo = f"ocorrencia_{despesa.id}_comprovante.{ext}"
                    zf.writestr(nome_arquivo, data)

                    # Remove do Cloudinary usando o public_id
                    public_id = despesa.comprovante.name.rsplit('.', 1)[0]
                    cloudinary.uploader.destroy(public_id, resource_type='raw', invalidate=True)
                    cloudinary.uploader.destroy(public_id, resource_type='image', invalidate=True)

                    despesa.comprovante = None
                    despesa.save(update_fields=['comprovante'])
                    total += 1
                except Exception:
                    erros += 1

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="comprovantes_malupe.zip"'

        msg = f"{total} comprovante(s) baixado(s) e removido(s) da nuvem."
        if erros:
            msg += f" {erros} arquivo(s) com erro (mantidos na nuvem)."
        self.message_user(request, msg)
        return response

    baixar_e_limpar_comprovantes.short_description = "⬇ Baixar comprovantes e liberar espaço na nuvem"

    list_display = ('id', 'data_criacao_display', 'tipo_badge', 'solicitante', 'despesa_display',
                    'valor_formatado', 'data_ultimo_status', 'hora_ultimo_status', 'status_badge', 'botao_detalhes')
    list_filter = (
        'tipo_lancamento',
        'status',
        ('data_criacao', DateRangeFilterBuilder(title='Data da Solicitação')),
        ('data_ultima_alteracao', DateRangeFilterBuilder(title='Última Troca de Status')),
        WfIdFilter,
        WfSolicitanteFilter,
        WfDespesaFilter,
    )
    search_fields = ('id', 'fornecedor__razao_social', 'solicitante__first_name')

    CORES_SISTEMA = {
        'AGUARDANDO_COMERCIAL': '#1abc9c',
        'AGUARDANDO_ADM': '#e67e22',
        'AGUARDANDO_RH': '#f39c12',
        'AGUARDANDO_FIN': '#3498db',
        'DIRECIONADO_OP': '#9b59b6',
        'PAGO': '#27ae60',
        'CONFERIDO': '#1a7a4a',
        'RASCUNHO': '#95a5a6',
        'CANCELADO': '#c0392b'
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in form.base_fields.values():
            if hasattr(field.widget, 'can_add_related'):
                field.widget.can_add_related = False
                field.widget.can_change_related = False
                field.widget.can_delete_related = False
                field.widget.can_view_related = False

        class RequestDespesaForm(form):
            def __init__(self, *args, **kwargs):
                kwargs['request'] = request
                super().__init__(*args, **kwargs)

        return RequestDespesaForm

    # --- VISIBILIDADE ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if user.is_superuser:
            return qs

        grupos = list(user.groups.values_list('name', flat=True))

        # Financeiro e Operador enxergam tudo
        if 'Aprovador Financeiro' in grupos or 'Operador' in grupos:
            return qs

        # RH: seus próprios + solicitações/extras em AGUARDANDO_RH + já atuou
        # Caixinhas de outros perfis nunca passam pelo RH
        if 'Aprovador RH' in grupos:
            return qs.filter(
                Q(solicitante=user) |
                Q(status='AGUARDANDO_RH', tipo_lancamento__in=['SOLICITACAO', 'EXTRA']) |
                Q(logs__usuario=user)
            ).distinct()

        # Comercial: somente caixinhas feitas por ele
        if 'Comercial' in grupos:
            return qs.filter(solicitante=user, tipo_lancamento='CAIXINHA')

        # Administrativo: seus próprios registros + extras direcionados a ele
        filtro_base = Q(solicitante=user)
        if 'Administrativo' in grupos:
            filtro_base |= Q(lancamentoextra__administrativo=user)

        return qs.filter(filtro_base).distinct()

    # --- CAMPOS TRAVADOS (READONLY) ---
    def get_readonly_fields(self, request, obj=None):
        ro_fields = ['tipo_lancamento', 'data_ultima_alteracao', 'dialogo_display']

        # Novo registro para usuário comum: status é auto-definido, exibe só-leitura
        if not obj and not request.user.is_superuser:
            ro_fields.append('status')
            return ro_fields

        if obj:
            user = request.user
            grupos = list(user.groups.values_list('name', flat=True))

            if user.is_superuser:
                return ['dialogo_display']  # campo calculado, sempre readonly

            if not self.has_change_permission(request, obj):
                return [f.name for f in self.model._meta.fields]

            # ADM com ocorrência na sua fila: pode editar qualquer campo
            if 'Administrativo' in grupos and obj.status == 'AGUARDANDO_ADM':
                return ro_fields

            # Aprovador RH com EXTRA na sua fila: libera campos de pagamento
            if 'Aprovador RH' in grupos and obj.status == 'AGUARDANDO_RH' and obj.tipo_lancamento == 'EXTRA':
                return ro_fields

            campos_travados_padrao = [
                'solicitante', 'data_despesa', 'fornecedor', 'valor', 'observacoes',
                'comprovante', 'inicio_cobertura', 'fim_cobertura', 'dias_cobertura',
                'tomador', 'filial', 'motivo_ausencia', 'colaborador_faltou',
                'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto'
            ]
            ro_fields.extend(campos_travados_padrao)

            if not ('Aprovador Financeiro' in grupos or 'Operador' in grupos):
                ro_fields.extend(['operador'])

        return ro_fields

    # --- FIELDSETS ---
    def get_fieldsets(self, request, obj=None):
        user = request.user
        grupos = list(user.groups.values_list('name', flat=True))

        tipo = obj.tipo_lancamento if obj else request.GET.get('tipo', 'CAIXINHA')

        if tipo == 'CAIXINHA':
            campos_lancamento = (
                'tipo_reserva',
                ('tipo_lancamento', 'data_despesa'),
                ('fornecedor', 'valor'),
                ('solicitante', 'comprovante'),
                'observacoes'
            )
        elif tipo == 'SOLICITACAO':
            campos_lancamento = (
                'tipo_reserva',
                ('tipo_lancamento', 'data_despesa'),
                ('fornecedor', 'valor'),
                ('tomador', 'filial'),
                ('motivo_ausencia', 'colaborador_faltou'),
                'dias_cobertura',
                'solicitante',
                ('nome_cobriu', 'dados_bancarios_pagto'),
                'observacoes'
            )
        else:  # EXTRA
            campos_lancamento = (
                'tipo_reserva',
                ('tipo_lancamento', 'data_despesa'),
                ('fornecedor', 'valor'),
                ('tomador', 'filial'),
                ('motivo_ausencia', 'colaborador_faltou'),
                'dias_cobertura',
                'solicitante',
                'observacoes'
            )

        fieldsets = [
            ('Dados do Lançamento', {
                'fields': campos_lancamento
            }),
        ]

        if obj and obj.tipo_lancamento == 'EXTRA':
            fieldsets.append(('Definição de Pagamento (Administrativo)', {
                'fields': (
                    'nome_cobriu',
                    ('forma_pagamento', 'dados_bancarios_pagto')
                )
            }))

        # ── Aba "Aprovação / Execução" ─────────────────────────────────────────
        pode_ver_pagamento = (user.is_superuser or 'Aprovador Financeiro' in grupos or 'Operador' in grupos)
        is_aprovador = any(g in grupos for g in [
            'Aprovador Financeiro', 'Aprovador RH', 'Operador', 'Administrativo', 'Comercial'
        ])

        # ── Tela de CRIAÇÃO (novo registro) ───────────────────────────────────
        if not obj and not user.is_superuser:
            fieldsets.append(('Aprovação / Execução', {
                'fields': (),
                'description': mark_safe(
                    'O status será definido automaticamente ao salvar:<br>'
                    '<ul style="margin:8px 0 0 20px">'
                    '<li><strong>Caixinha</strong> → Aguardando Financeiro</li>'
                    '<li><strong>Solicitação</strong> → Aguardando RH</li>'
                    '<li><strong>Extra</strong> → Aguardando Administrativo</li>'
                    '</ul>'
                ),
            }))
            return fieldsets

        campos_aprovacao = ['status']

        # Campos extras só fazem sentido em registros existentes
        if obj:
            pode_editar = user.is_superuser or self.has_change_permission(request, obj)

            if user.is_superuser or 'Aprovador Financeiro' in grupos or 'Operador' in grupos:
                campos_aprovacao.append('operador')

            if pode_ver_pagamento:
                campos_aprovacao.append(('empresa_pagadora', 'banco_pagador'))

            # Motivo cancelamento e justificativa: apenas para quem pode agir
            if pode_editar:
                campos_aprovacao.append('motivo_cancelamento')

                pode_retornar = any(g in grupos for g in [
                    'Aprovador RH', 'Aprovador Financeiro', 'Operador'
                ])
                if user.is_superuser or pode_retornar:
                    campos_aprovacao.append('justificativa_retorno')

                # Campo mensagem livre para qualquer parte do fluxo responder
                campos_aprovacao.append('mensagem')

        fieldsets.append(('Aprovação / Execução', {
            'fields': tuple(campos_aprovacao)
        }))

        # ── Aba "Histórico / Diálogo" ──────────────────────────────────────
        if obj:
            fieldsets.append(('Histórico / Diálogo', {
                'fields': ('dialogo_display',),
            }))

        return fieldsets

    # --- PERMISSÕES ---
    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        user = request.user
        if user.is_superuser:
            return True

        grupos = list(user.groups.values_list('name', flat=True))

        # Usa sempre o status e tipo gravados no banco, não o valor em memória
        # (que pode ter sido modificado pelo POST antes da validação falhar)
        db_vals = Despesa.objects.filter(pk=obj.pk).values('status', 'tipo_lancamento').first()
        if db_vals:
            obj_status = db_vals['status']
            obj_tipo   = db_vals['tipo_lancamento']
        else:
            obj_status = obj.status
            obj_tipo   = obj.tipo_lancamento

        # Comercial: suas caixinhas (inclui devolvidas pelo Financeiro)
        if 'Comercial' in grupos and obj_tipo == 'CAIXINHA':
            if obj.solicitante == user and obj_status in ['AGUARDANDO_COMERCIAL', 'AGUARDANDO_ADM']:
                return True

        # Administrativo: seus próprios ao AGUARDANDO_ADM + extras direcionados a ele
        if 'Administrativo' in grupos and obj_status == 'AGUARDANDO_ADM':
            if obj.solicitante == user:
                return True
            try:
                if obj.lancamentoextra and obj.lancamentoextra.administrativo == user:
                    return True
            except Exception:
                pass

        # RH: apenas SOLICITACAO e EXTRA em AGUARDANDO_RH (caixinha não passa pelo RH)
        if 'Aprovador RH' in grupos and obj_status == 'AGUARDANDO_RH':
            if obj_tipo in ['SOLICITACAO', 'EXTRA']:
                return True

        # Financeiro
        if 'Aprovador Financeiro' in grupos:
            if obj_status in ['AGUARDANDO_FIN', 'DIRECIONADO_OP']:
                return True

        # Operador
        if 'Operador' in grupos and obj_status == 'DIRECIONADO_OP':
            return True

        if obj.solicitante == user and obj_status == 'RASCUNHO':
            return True

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

            grupos_user = list(request.user.groups.values_list('name', flat=True))

            if obj.tipo_lancamento == 'EXTRA':
                # EXTRA sempre começa no Administrativo (criado por outro perfil)
                obj.status = 'AGUARDANDO_ADM'
            elif obj.tipo_lancamento == 'CAIXINHA':
                # Qualquer perfil que crie uma caixinha já aprova na criação
                obj.status = 'AGUARDANDO_FIN'
            else:  # SOLICITACAO
                if 'Aprovador RH' in grupos_user:
                    # RH não aprova o próprio pedido — vai direto ao Financeiro
                    obj.status = 'AGUARDANDO_FIN'
                else:
                    obj.status = 'AGUARDANDO_RH'

            acao_log = "Criou Registro"
        else:
            # Detecta ação específica pelo status novo
            status_novo = obj.status
            if status_novo == 'AGUARDANDO_RH' and 'status' in form.changed_data:
                acao_log = "Aprovou → RH"
            elif status_novo == 'AGUARDANDO_FIN' and 'status' in form.changed_data:
                grupos_user = list(request.user.groups.values_list('name', flat=True))
                if 'Operador' in grupos_user:
                    acao_log = "Devolveu ao Financeiro"
                else:
                    acao_log = "Aprovou → Financeiro"
            elif status_novo == 'AGUARDANDO_ADM' and 'status' in form.changed_data:
                acao_log = "Retornou ao Administrativo"
            elif status_novo == 'DIRECIONADO_OP' and 'status' in form.changed_data:
                acao_log = "Direcionou ao Operador"
            elif status_novo == 'PAGO' and 'status' in form.changed_data:
                acao_log = "FINALIZOU (PAGO)"
            elif status_novo == 'CONFERIDO' and 'status' in form.changed_data:
                acao_log = "CONFERIDO"
            elif status_novo == 'CANCELADO' and 'status' in form.changed_data:
                acao_log = "CANCELOU"
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

        if change and obj.status == 'CONFERIDO' and obj.tipo_lancamento == 'CAIXINHA' and 'status' in form.changed_data:
            self.registrar_utilizacao_supervisor(obj, request)

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
        elif 'Comercial' in grupos:
            perfil = "Comercial"

        obs = f"Status: {obj.get_status_display()}"
        if obj.operador:
            obs += f" → {obj.operador.first_name}"
        if 'valor' in form.changed_data:
            obs += f" | Valor alterado para R$ {obj.valor}"

        # Questionamento / justificativa de retorno
        justificativa = form.cleaned_data.get('justificativa_retorno', '').strip()
        if justificativa and 'justificativa_retorno' in form.changed_data:
            obs += f"\n[QUESTIONAMENTO] {justificativa}"

        # Mensagem livre adicionada pelo usuário
        mensagem_livre = form.cleaned_data.get('mensagem', '').strip()
        if mensagem_livre:
            obs += f"\n[MENSAGEM] {mensagem_livre}"

        LogWorkflow.objects.create(
            despesa=obj,
            usuario=request.user,
            perfil_usuario=perfil,
            acao=acao_log,
            observacao=obs
        )

    def gerar_contas_a_pagar(self, despesa, request):
        if not despesa.banco_pagador or not despesa.empresa_pagadora:
            self.message_user(
                request,
                "⚠️ Conta a Pagar NÃO gerada: Banco ou Empresa Pagadora não informados.",
                level='WARNING'
            )
            return

        if not ContasAPagar.objects.filter(nota=f"WF-{despesa.id}").exists():
            partes_obs = [f"Ref. Workflow #{despesa.id} — {despesa.get_tipo_lancamento_display()}"]
            if despesa.filial:
                partes_obs.append(f"Filial: {despesa.filial}")
            if despesa.nome_cobriu:
                partes_obs.append(f"Nome quem cobriu: {despesa.nome_cobriu}")
            if despesa.dados_bancarios_pagto:
                partes_obs.append(f"Dados p/ pagamento: {despesa.dados_bancarios_pagto}")
            ContasAPagar.objects.create(
                fornecedor=despesa.fornecedor,
                empresa_pagadora=despesa.empresa_pagadora,
                banco=despesa.banco_pagador,
                data_emissao=despesa.data_despesa,
                vencimento=timezone.now().date(),
                valor=despesa.valor,
                nota=f"WF-{despesa.id}",
                status='PAGO',
                data_baixa=timezone.now().date(),
                usuario_baixa=request.user,
                observacoes=" | ".join(partes_obs),
                plano_de_contas=despesa.fornecedor.plano_de_contas,
            )

    def registrar_utilizacao_supervisor(self, despesa, request):
        from financeiro.models import SaldoSupervisor, MovimentacaoSupervisor
        supervisor = despesa.solicitante
        saldo_sup = SaldoSupervisor.objects.filter(
            supervisor=supervisor, status='ABERTO'
        ).order_by('-data_inicio').first()
        if not saldo_sup:
            self.message_user(request, f"⚠️ Nenhuma linha de saldo aberta para {supervisor}. Crie em Saldo Supervisores.", level='WARNING')
            return
        MovimentacaoSupervisor.objects.create(
            saldo_supervisor=saldo_sup,
            tipo='DEBITO',
            valor=despesa.valor,
            descricao=f"Caixinha #{despesa.id} — {despesa.fornecedor}",
            referencia_despesa_id=despesa.id,
        )

    def changelist_view(self, request, extra_context=None):
        extra = extra_context or {}
        extra['status_choices'] = STATUS_WORKFLOW
        extra['solicitantes_opts'] = list(
            UsuarioCustomizado.objects.filter(solicitacoes__isnull=False)
            .values_list('id', 'first_name', 'last_name').distinct().order_by('first_name')
        )
        response = super().changelist_view(request, extra_context=extra)
        if not hasattr(response, 'context_data'):
            return response
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            qs = Despesa.objects.none()
        ids_distintos = qs.order_by().values_list('id', flat=True).distinct()
        metrics = Despesa.objects.filter(id__in=ids_distintos).values('status').annotate(total_valor=Sum('valor'), total_qtd=Count('id'))
        summary = []
        for item in metrics:
            st = item['status']
            cor = self.CORES_SISTEMA.get(st, '#95a5a6')
            if 'CANCELADO' in st:
                cor = self.CORES_SISTEMA['CANCELADO']
            summary.append({
                'status_key': st,
                'status_label': dict(Despesa._meta.get_field('status').choices).get(st, st),
                'total_valor': item['total_valor'],
                'total_qtd': item['total_qtd'],
                'color': cor
            })
        response.context_data['summary_data'] = summary
        return response

    def despesa_display(self, obj):
        if obj.tipo_lancamento == 'EXTRA' and obj.tomador:
            return obj.tomador.nome
        return obj.fornecedor.razao_social if obj.fornecedor else '-'

    despesa_display.short_description = "Despesa"

    def valor_formatado(self, obj):
        return f"R$ {obj.valor}"

    valor_formatado.short_description = "Valor"

    def status_badge(self, obj):
        cor = self.CORES_SISTEMA.get(obj.status, '#95a5a6')
        if 'CANCELADO' in obj.status:
            cor = self.CORES_SISTEMA['CANCELADO']
        style = (
            f'color:white; background-color:{cor}; padding:5px; border-radius:10px; '
            f'font-weight:bold; font-size:11px; display: inline-block; width: 140px; text-align: center;'
        )
        return mark_safe(f'<span style="{style}">{obj.get_status_display()}</span>')

    status_badge.short_description = "Status"

    def tipo_badge(self, obj):
        if obj.tipo_lancamento == 'CAIXINHA':
            cor = '#34495e'
        elif obj.tipo_lancamento == 'EXTRA':
            cor = '#e67e22'
        else:
            cor = '#17a2b8'
        style = (
            f'color:white; background-color:{cor}; padding:5px; border-radius:4px; '
            f'display: inline-block; width: 100px; text-align: center;'
        )
        return mark_safe(f'<span style="{style}">{obj.get_tipo_lancamento_display()}</span>')

    tipo_badge.short_description = "Tipo"

    def botao_detalhes(self, obj):
        return mark_safe(f'<a class="button" href="{obj.id}/change/">🔎 Ver</a>')

    botao_detalhes.short_description = "Ação"

    def data_criacao_display(self, obj):
        if obj.data_criacao:
            from django.utils import timezone as tz
            return tz.localtime(obj.data_criacao).strftime('%d/%m/%Y')
        return '—'

    data_criacao_display.short_description = "Criado em"
    data_criacao_display.admin_order_field = 'data_criacao'

    def data_ultimo_status(self, obj):
        if obj.data_ultima_alteracao:
            from django.utils import timezone as tz
            return tz.localtime(obj.data_ultima_alteracao).strftime('%d/%m/%Y')
        return '—'

    data_ultimo_status.short_description = "Últ. Status"
    data_ultimo_status.admin_order_field = 'data_ultima_alteracao'

    def hora_ultimo_status(self, obj):
        if obj.data_ultima_alteracao:
            from django.utils import timezone as tz
            return tz.localtime(obj.data_ultima_alteracao).strftime('%H:%M')
        return '—'

    hora_ultimo_status.short_description = "Hora"
    hora_ultimo_status.admin_order_field = 'data_ultima_alteracao'

    def dialogo_display(self, obj):
        """Exibe o histórico de ações como um diálogo cronológico."""
        if not obj or not obj.pk:
            return '—'
        logs = obj.logs.order_by('data_hora')
        if not logs.exists():
            return '—'

        CORES_PERFIL = {
            'Administrativo': '#e67e22',
            'RH':             '#f39c12',
            'Financeiro':     '#3498db',
            'Operador':       '#9b59b6',
            'Comercial':      '#1abc9c',
            'Admin':          '#2c3e50',
            'Solicitante':    '#7f8c8d',
        }

        html = '<div style="display:flex;flex-direction:column;gap:12px;padding:8px 0;">'
        for log in logs:
            from django.utils import timezone as tz
            dt = tz.localtime(log.data_hora).strftime('%d/%m/%Y %H:%M')
            cor = CORES_PERFIL.get(log.perfil_usuario, '#95a5a6')
            nome = log.usuario.get_full_name() or log.usuario.username

            # Separa linhas de observação
            obs_raw = log.observacao or ''
            linhas = obs_raw.split('\n')
            status_line = linhas[0] if linhas else ''
            extras = [l for l in linhas[1:] if l.strip()]

            corpo = f'<span style="font-size:12px;color:#555;">{status_line}</span>'
            for extra in extras:
                if extra.startswith('[QUESTIONAMENTO]'):
                    texto = extra.replace('[QUESTIONAMENTO]', '').strip()
                    corpo += f'<div style="margin-top:6px;background:#fff3cd;border-left:3px solid #f39c12;padding:6px 10px;border-radius:4px;"><strong>❓ Questionamento:</strong> {texto}</div>'
                elif extra.startswith('[MENSAGEM]'):
                    texto = extra.replace('[MENSAGEM]', '').strip()
                    corpo += f'<div style="margin-top:6px;background:#d4edda;border-left:3px solid #28a745;padding:6px 10px;border-radius:4px;"><strong>💬 Mensagem:</strong> {texto}</div>'

            html += f'''
            <div style="border-left:4px solid {cor};padding:8px 12px;background:#fafafa;border-radius:0 6px 6px 0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="background:{cor};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;">{log.perfil_usuario}</span>
                    <strong style="font-size:13px;">{nome}</strong>
                    <span style="font-size:11px;color:#888;">{dt}</span>
                    <span style="margin-left:auto;font-size:11px;font-style:italic;color:#666;">{log.acao}</span>
                </div>
                {corpo}
            </div>'''

        html += '</div>'
        return mark_safe(html)

    dialogo_display.short_description = "Histórico de Diálogo"