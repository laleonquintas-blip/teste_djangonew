# extras/admin.py

from django.contrib import admin
from .models import LancamentoExtra

@admin.register(LancamentoExtra)
class LancamentoExtraAdmin(admin.ModelAdmin):
    # 1. LISTAGEM
    list_display = ('nota_fiscal', 'data_emissao', 'empresa_prestadora', 'valor_recebimento', 'status_workflow')
    list_filter = ('empresa_prestadora', 'banco_recebimento', 'administrativo')
    search_fields = ('nota_fiscal', 'valor_recebimento')

    # 2. ORGANIZAÇÃO DO FORMULÁRIO
    fieldsets = (
        ('Dados Principais', {
            'fields': (
                ('nota_fiscal', 'tipo_fixo'),
                ('data_emissao', 'data_vencimento'),
                ('empresa_prestadora', 'banco_recebimento'),
                'valor_recebimento',
                'administrativo'
            )
        }),
        ('Detalhes da Solicitação', {
            'fields': (
                ('inicio_cobertura', 'fim_cobertura'),
                ('tomador', 'filial'),
                ('motivo_ausencia', 'colaborador_faltou'),
            )
        }),
        ('Integrações', {
            'classes': ('collapse',),
            'fields': ('conta_receber_criada', 'workflow_criado')
        }),
    )

    readonly_fields = ('nota_fiscal', 'data_emissao', 'tipo_fixo', 'conta_receber_criada', 'workflow_criado')

    def status_workflow(self, obj):
        if obj.workflow_criado:
            return obj.workflow_criado.get_status_display()
        return "Pendente"
    status_workflow.short_description = "Status Workflow"

    # --- SOLUÇÃO DEFINITIVA PARA REMOVER ÍCONES E ALINHAR ---
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Varre todos os campos do formulário
        for field in form.base_fields.values():
            # Se o campo tiver os atributos de adicionar/alterar (é um ForeignKey)
            if hasattr(field.widget, 'can_add_related'):
                field.widget.can_add_related = False
                field.widget.can_change_related = False
                field.widget.can_delete_related = False
                field.widget.can_view_related = False
        return form

    class Media:
        css = {
            'all': ('css/admin_fixes.css',)
        }