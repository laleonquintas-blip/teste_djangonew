# extras/admin.py

from django.contrib import admin
from .models import LancamentoExtra


@admin.register(LancamentoExtra)
class LancamentoExtraAdmin(admin.ModelAdmin):
    # 1. LISTAGEM (Removidos campos que não existem mais)
    list_display = ('nota_fiscal', 'data_emissao', 'empresa_prestadora', 'valor_recebimento', 'status_workflow')
    list_filter = ('empresa_prestadora', 'banco_recebimento', 'administrativo')
    search_fields = ('nota_fiscal', 'valor_recebimento')

    # 2. ORGANIZAÇÃO DO FORMULÁRIO
    # Removi 'nome_cobriu', 'forma_pagamento', 'dados_bancarios_pagto' desta lista
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
                # Campos de pagamento removidos daqui
            )
        }),
        ('Integrações', {
            'classes': ('collapse',),
            'fields': ('conta_receber_criada', 'workflow_criado')
        }),
    )

    # 3. CAMPOS SOMENTE LEITURA
    readonly_fields = ('nota_fiscal', 'data_emissao', 'tipo_fixo', 'conta_receber_criada', 'workflow_criado')

    # 4. STATUS VISUAL
    def status_workflow(self, obj):
        if obj.workflow_criado:
            return obj.workflow_criado.get_status_display()
        return "Pendente"

    status_workflow.short_description = "Status Workflow"