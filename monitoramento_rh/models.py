from django.db import models
from django.contrib.auth import get_user_model
from cadastros.models import Tomador, Filial, Fornecedor, Banco, PlanoDeContas, validar_cpf
from financeiro.models import Empresa

User = get_user_model()


class CoberturasRH(models.Model):
    class Meta:
        managed = False
        verbose_name = 'Coberturas de Falta'
        verbose_name_plural = 'Coberturas de Falta'
        app_label = 'monitoramento_rh'


class Folha(models.Model):
    TIPO_CHOICES = [
        ('SEMANAL',    'Semanal'),
        ('QUINZENAL',  'Quinzenal'),
    ]
    tomador          = models.ForeignKey(Tomador, on_delete=models.PROTECT, verbose_name='Tomador')
    tipo             = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name='Periodicidade')
    descricao        = models.CharField(max_length=200, blank=True, verbose_name='Descrição')
    fornecedor       = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Fornecedor (contábil)')
    empresa_pagadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Empresa Pagadora')
    plano_de_contas  = models.ForeignKey(PlanoDeContas, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Plano de Contas')
    ativa            = models.BooleanField(default=True, verbose_name='Ativa')
    criado_em        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.tomador} — {self.get_tipo_display()}'

    class Meta:
        verbose_name = 'Folha'
        verbose_name_plural = 'Folhas'
        ordering = ['tomador__nome', 'tipo']


class ColaboradorInformal(models.Model):
    folha     = models.ForeignKey(Folha, on_delete=models.CASCADE, related_name='colaboradores', verbose_name='Folha')
    filial    = models.ForeignKey(Filial, on_delete=models.PROTECT, verbose_name='Filial')
    qt        = models.PositiveIntegerField(verbose_name='Qt')
    nome      = models.CharField(max_length=200, verbose_name='Nome')
    cpf       = models.CharField(max_length=14, verbose_name='CPF', validators=[validar_cpf])
    registro  = models.BooleanField(default=False, verbose_name='Registro')
    banco     = models.CharField(max_length=100, verbose_name='Banco (depósito)')
    agencia   = models.CharField(max_length=20, verbose_name='Agência')
    conta     = models.CharField(max_length=30, verbose_name='Conta')
    valor_padrao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor padrão')
    ativo     = models.BooleanField(default=True, verbose_name='Ativo na folha')

    def __str__(self):
        return f'{self.nome} ({self.folha})'

    class Meta:
        verbose_name = 'Colaborador Informal'
        verbose_name_plural = 'Colaboradores Informais'
        ordering = ['banco', 'nome']


STATUS_PAGAMENTO = [
    ('RASCUNHO',       'Rascunho'),
    ('ENVIADA',        'Enviada para aprovação'),
    ('AGUARDANDO_RH',  'Aguardando RH'),
    ('AGUARDANDO_FIN', 'Aguardando Financeiro'),
    ('PAGA',           'Paga'),
    ('CANCELADA',      'Cancelada'),
]


class PagamentoFolha(models.Model):
    folha            = models.ForeignKey(Folha, on_delete=models.PROTECT, related_name='pagamentos', verbose_name='Folha')
    data_inicio      = models.DateField(verbose_name='Competência início')
    data_fim         = models.DateField(verbose_name='Competência fim')
    status           = models.CharField(max_length=20, choices=STATUS_PAGAMENTO, default='RASCUNHO', verbose_name='Status')
    total            = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total')
    banco_pagamento  = models.ForeignKey(Banco, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Banco de Pagamento')
    criado_por       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+', verbose_name='Criado por')
    aprovado_rh_por  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Aprovado (RH) por')
    aprovado_rh_em   = models.DateTimeField(null=True, blank=True)
    pago_por         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Pago por')
    criado_em        = models.DateTimeField(auto_now_add=True)
    pago_em          = models.DateTimeField(null=True, blank=True, verbose_name='Pago em')
    observacao       = models.TextField(blank=True, verbose_name='Observação')

    def __str__(self):
        return f'{self.folha} | {self.data_inicio} → {self.data_fim}'

    class Meta:
        verbose_name = 'Pagamento de Folha'
        verbose_name_plural = 'Pagamentos de Folha'
        ordering = ['-data_inicio']


class ItemPagamento(models.Model):
    pagamento        = models.ForeignKey(PagamentoFolha, on_delete=models.CASCADE, related_name='itens', verbose_name='Pagamento')
    colaborador      = models.ForeignKey(ColaboradorInformal, on_delete=models.PROTECT, verbose_name='Colaborador')
    valor_anterior   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Valor anterior')
    valor_atual      = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor atual')
    justificativa    = models.TextField(blank=True, verbose_name='Justificativa da diferença')

    def __str__(self):
        return f'{self.colaborador.nome} — R$ {self.valor_atual}'

    class Meta:
        verbose_name = 'Item de Pagamento'
        verbose_name_plural = 'Itens de Pagamento'
        ordering = ['colaborador__banco', 'colaborador__nome']
