from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import ContasAPagar, ContasAReceber
from cadastros.models import Fornecedor, Empresa, Banco, PlanoDeContas, Cliente
from core.models import UsuarioCustomizado


class ContasAPagarResource(resources.ModelResource):

    fornecedor = fields.Field(
        column_name='Fornecedor',
        attribute='fornecedor',
        widget=ForeignKeyWidget(Fornecedor, 'razao_social'),
    )
    empresa_pagadora = fields.Field(
        column_name='Empresa Pagadora',
        attribute='empresa_pagadora',
        widget=ForeignKeyWidget(Empresa, 'nome'),
    )
    banco = fields.Field(
        column_name='Banco',
        attribute='banco',
        widget=ForeignKeyWidget(Banco, 'nome'),
    )
    plano_de_contas = fields.Field(
        column_name='Plano de Contas',
        attribute='plano_de_contas',
        widget=ForeignKeyWidget(PlanoDeContas, 'nome'),
    )
    responsavel_pagamento = fields.Field(
        column_name='Responsável pelo Pagamento',
        attribute='responsavel_pagamento',
        widget=ForeignKeyWidget(UsuarioCustomizado, 'first_name'),
    )
    supervisor = fields.Field(
        column_name='Supervisor',
        attribute='supervisor',
        widget=ForeignKeyWidget(UsuarioCustomizado, 'first_name'),
    )
    usuario_baixa = fields.Field(
        column_name='Usuário da Baixa',
        attribute='usuario_baixa',
        widget=ForeignKeyWidget(UsuarioCustomizado, 'first_name'),
    )

    def dehydrate_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = ContasAPagar
        fields = (
            'nota',
            'fornecedor',
            'empresa_pagadora',
            'banco',
            'plano_de_contas',
            'data_emissao',
            'vencimento',
            'valor',
            'status',
            'data_baixa',
            'usuario_baixa',
            'responsavel_pagamento',
            'supervisor',
            'observacoes',
        )
        export_order = fields


class ContasAReceberResource(resources.ModelResource):

    cliente = fields.Field(
        column_name='Cliente',
        attribute='cliente',
        widget=ForeignKeyWidget(Cliente, 'razao_social'),
    )
    empresa_prestadora = fields.Field(
        column_name='Empresa Prestadora',
        attribute='empresa_prestadora',
        widget=ForeignKeyWidget(Empresa, 'nome'),
    )
    banco = fields.Field(
        column_name='Banco',
        attribute='banco',
        widget=ForeignKeyWidget(Banco, 'nome'),
    )
    usuario_baixa = fields.Field(
        column_name='Usuário da Baixa',
        attribute='usuario_baixa',
        widget=ForeignKeyWidget(UsuarioCustomizado, 'first_name'),
    )

    def dehydrate_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = ContasAReceber
        fields = (
            'nota',
            'cliente',
            'empresa_prestadora',
            'banco',
            'data_emissao',
            'vencimento',
            'valor',
            'status',
            'data_baixa',
            'usuario_baixa',
            'escala_horas',
            'observacoes',
        )
        export_order = fields
