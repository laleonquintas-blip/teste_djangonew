# financeiro/models.py

from django.db import models
from django.contrib import messages
from datetime import date # <--- (NOVO) Importação para pegar a data de hoje
from cadastros.models import Cliente, Fornecedor, Empresa, Banco, TipoServico
from core.models import UsuarioCustomizado  # Import único para o usuário

# --- CHOICES (Opções Fixas) ---
STATUS_PAGAMENTO_CHOICES = [
    ('PENDENTE', 'Pendente'),
    ('PAGO', 'Pago'),
    ('CANCELADO', 'Cancelado'),
]


# --- 1. MODELO SEQUENCIAL (CONTADOR) ---
class Sequencial(models.Model):
    # 'CP' para Contas a Pagar, 'CR' para Contas a Receber
    prefixo = models.CharField(max_length=5, unique=True, verbose_name="Prefixo")
    ultimo_numero = models.IntegerField(default=0, verbose_name="Último Número Gerado")

    def __str__(self):
        return f"Contador {self.prefixo}: {self.ultimo_numero}"

    class Meta:
        verbose_name = "Contador Sequencial"
        verbose_name_plural = "Contadores Sequenciais"


# --- 2. CONTAS A PAGAR (CP) ---
class ContasAPagar(models.Model):
    # Conexões
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, verbose_name="Fornecedor")
    empresa_pagadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa Pagadora")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name="Banco de Pagamento")

    # Dados da Conta
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    vencimento = models.DateField(verbose_name="Vencimento")
    nota = models.CharField(max_length=50, unique=True, verbose_name="Nº da Nota Fiscal")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    conta_contabil = models.CharField(max_length=50, blank=True, verbose_name="Conta Contábil")

    # Status e Controle
    status = models.CharField(max_length=15, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE',
                              verbose_name="Status")
    data_baixa = models.DateField(null=True, blank=True, verbose_name="Data de Baixa/Pagamento")

    # Quem baixou
    usuario_baixa = models.ForeignKey(UsuarioCustomizado, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name="Usuário da Baixa")

    def save(self, request=None, *args, **kwargs):
        # 1. Gera Nota se não existir
        if not self.nota:
            contador, created = Sequencial.objects.get_or_create(
                prefixo='CP', defaults={'ultimo_numero': 0}
            )
            contador.ultimo_numero += 1
            contador.save()
            self.nota = f"CP-{contador.ultimo_numero:05d}"

            if request:
                messages.success(request, f"SUCESSO! Conta a Pagar criada: {self.nota}")

        # 2. (NOVO) LÓGICA DA DATA AUTOMÁTICA
        # Se mudou para PAGO e a data está vazia, preenche com HOJE
        if self.status == 'PAGO' and not self.data_baixa:
            self.data_baixa = date.today()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Conta a Pagar"
        verbose_name_plural = "Contas a Pagar"


# --- 3. CONTAS A RECEBER (CR) ---
class ContasAReceber(models.Model):
    # Conexões
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    empresa_prestadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa Prestadora")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name="Banco de Recebimento")

    # Dados da Conta
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    vencimento = models.DateField(verbose_name="Vencimento")
    nota = models.CharField(max_length=50, unique=True, verbose_name="Nº da Nota Fiscal")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    escala_horas = models.CharField(max_length=50, blank=True, verbose_name="Escala de Horas")
    observacoes = models.TextField(blank=True, verbose_name="Observações")

    # Status e Controle
    status = models.CharField(max_length=15, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE',
                              verbose_name="Status")
    data_baixa = models.DateField(null=True, blank=True, verbose_name="Data de Baixa/Recebimento")

    # Quem baixou
    usuario_baixa = models.ForeignKey(UsuarioCustomizado, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name="Usuário da Baixa")

    def save(self, request=None, *args, **kwargs):
        # 1. Gera Nota se não existir
        if not self.nota:
            contador, created = Sequencial.objects.get_or_create(
                prefixo='CR', defaults={'ultimo_numero': 0}
            )
            contador.ultimo_numero += 1
            contador.save()
            self.nota = f"CR-{contador.ultimo_numero:05d}"

            if request:
                messages.success(request, f"SUCESSO! Conta a Receber criada: {self.nota}")

        # 2. (NOVO) LÓGICA DA DATA AUTOMÁTICA
        if self.status == 'PAGO' and not self.data_baixa:
            self.data_baixa = date.today()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Conta a Receber"
        verbose_name_plural = "Contas a Receber"


# --- 4. BASE SALDO (O Consolidador Automático) ---
class BaseSaldo(models.Model):
    # Campos de Controle
    origem = models.CharField(max_length=10, verbose_name="Origem")  # 'CP' ou 'CR'
    id_origem = models.IntegerField(verbose_name="ID Original")  # ID da conta original

    # Campos Visuais
    nome = models.CharField(max_length=200, verbose_name="Nome (Forn/Cli)")
    empresa = models.CharField(max_length=200, verbose_name="Empresa")
    data_emissao = models.DateField(verbose_name="Emissão")
    banco = models.CharField(max_length=100, verbose_name="Banco")
    vencimento = models.DateField(verbose_name="Vencimento")

    # Valor (+ para Entrada, - para Saída)
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor Líquido")

    status = models.CharField(max_length=50, verbose_name="Status")
    data_baixa = models.DateField(null=True, verbose_name="Data Baixa")
    usuario_baixa = models.CharField(max_length=150, null=True, blank=True, verbose_name="Usuário que Baixou")

    def __str__(self):
        return f"{self.data_baixa} | {self.nome} | R$ {self.valor}"

    class Meta:
        verbose_name = "Base de Saldo (Extrato)"
        verbose_name_plural = "Base de Saldos (Extrato)"
        ordering = ['-data_baixa']