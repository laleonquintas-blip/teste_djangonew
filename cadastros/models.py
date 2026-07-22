from django.db import models
from django.core.exceptions import ValidationError
import re


def validar_cpf(value):
    cpf = re.sub(r'\D', '', value or '')
    if not cpf:
        return
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido.')
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[i]):
            raise ValidationError('CPF inválido.')


# --- MODELOS SIMPLES ---

class Banco(models.Model):
    # O Django cria um campo 'id' automático que será nosso Código (ex: 1, 2, 3)
    nome = models.CharField(max_length=100, verbose_name="Nome do Banco")
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Saldo Inicial")
    entra_no_saldo_geral = models.BooleanField(
        default=True,
        verbose_name="Entra no Saldo Geral",
        help_text="Se desmarcado, a conta continua ativa no sistema mas não soma no card de Saldo Geral do dashboard."
    )

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"


class Empresa(models.Model):
    # Código será o ID automático
    nome = models.CharField(max_length=100, verbose_name="Nome da Empresa")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"


class TipoServico(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Tipo de Servico")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tipo de Servico"
        verbose_name_plural = "Tipos de Servicos"


class MotivoAusencia(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Motivo da Ausência")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Motivo"
        verbose_name_plural = "Motivos"


class Filial(models.Model): # <-- MOVIMENTO PARA CÁ E ALINHADA CORRETAMENTE
    # O ID automático será o código
    nome = models.CharField(max_length=100, verbose_name="Nome da Filial")
    cnpj = models.CharField(max_length=20, unique=True, verbose_name="CNPJ (Opcional)", blank=True, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiais" # Corrige a exibição no Admin


class Colaborador(models.Model):
    # Campos para Carga em Massa
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=20, unique=True, validators=[validar_cpf])
    departamento = models.CharField(max_length=100, blank=True)
    empresa = models.CharField(max_length=100, blank=True)  # Texto simples para facilitar importação excel
    filial = models.ForeignKey('Filial', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Filial")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"


class ColaboradorInfo(models.Model):
    TIPO_PIX_CHOICES = [
        ('CPF', 'CPF'),
        ('TELEFONE', 'Telefone'),
        ('EMAIL', 'E-mail'),
        ('ALEATORIA', 'Chave Aleatória'),
        ('BANCO', 'Dados Bancários'),
    ]
    nome = models.CharField(max_length=200, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=20, verbose_name="CPF", validators=[validar_cpf])
    tipo_pix = models.CharField(max_length=10, choices=TIPO_PIX_CHOICES, blank=True, verbose_name="Tipo de Chave")
    chave_pix = models.CharField(max_length=200, blank=True, verbose_name="Chave Pix / Dados Bancários")
    observacoes = models.TextField(blank=True, verbose_name="Observações")

    def __str__(self):
        return self.nome.upper()

    class Meta:
        verbose_name = "Cad. Folguista"
        verbose_name_plural = "Cad. Folguistas"
        ordering = ['nome']


class Tomador(models.Model):
    # Campos para Carga em Massa
    nome = models.CharField(max_length=200)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tomador"
        verbose_name_plural = "Tomadores"


# --- MODELOS FINANCEIROS ---

class Cliente(models.Model):
    TIPO_CHOICES = [
        ('FIXO', 'Fixo'),
        ('EVENTUAL', 'Eventual'),
    ]

    # Dados Básicos
    razao_social = models.CharField(max_length=200, verbose_name="Razão Social")
    cnpj_cpf = models.CharField(max_length=20, blank=True, verbose_name="CNPJ ou CPF")

    # Contrato
    dia_vencimento = models.IntegerField(null=True, blank=True, verbose_name="Dia de Vencimento (01-31)")
    valor_contrato = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor do Contrato")
    descricao_atividade = models.TextField(verbose_name="Descrição da Atividade", blank=True)
    forma_recebimento = models.CharField(max_length=100, verbose_name="Forma de Recebimento")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='EVENTUAL')

    # Controle
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.id} - {self.razao_social}"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"


class PlanoDeContas(models.Model):
    nome = models.CharField(max_length=150, verbose_name="Nome")
    conta_contabil = models.CharField(max_length=50, blank=True, verbose_name="Conta Contábil")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Plano de Contas"
        verbose_name_plural = "Plano de Contas"
        ordering = ['nome']


class Fornecedor(models.Model):
    razao_social = models.CharField(max_length=200, verbose_name="Razão Social")
    cnpj_cpf = models.CharField(max_length=20, unique=True, verbose_name="CNPJ ou CPF")
    forma_pagamento = models.CharField(max_length=100, verbose_name="Forma de Pagamento", blank=True)
    plano_de_contas = models.ForeignKey(
        PlanoDeContas, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Plano de Contas"
    )

    # A letra de acesso (A, B, C...) que você mencionou no Workflow
    letra_acesso = models.CharField(max_length=5, verbose_name="Letra de Acesso (Ex: A)", default='A')

    def __str__(self):
        return self.razao_social

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"