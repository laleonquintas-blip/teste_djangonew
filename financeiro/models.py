# financeiro/models.py

from django.db import models
from django.utils import timezone
from django.contrib import messages
from datetime import date
from django.utils.html import format_html
from cadastros.models import Cliente, Fornecedor, Empresa, Banco, TipoServico
from core.models import UsuarioCustomizado

STATUS_PAGAMENTO_CHOICES = [
    ('PENDENTE', 'Pendente'),
    ('PAGO', 'Pago'),
    ('CANCELADO', 'Cancelado'),
]

STATUS_TRANSFERENCIA_CHOICES = [
    ('DEFINITIVA',     '🟢 Definitiva'),
    ('TEMP_PENDENTE',  '🟡 Temporária (Pendente de Devolução)'),
    ('TEMP_DEVOLVIDA', '🔵 Temporária (Devolvida)'),
    ('CANCELADA',      '⚫ Cancelada'),
]


class Sequencial(models.Model):
    prefixo = models.CharField(max_length=5, unique=True, verbose_name="Prefixo")
    ultimo_numero = models.IntegerField(default=0, verbose_name="Último Número Gerado")

    def __str__(self):
        return f"Contador {self.prefixo}: {self.ultimo_numero}"

    class Meta:
        verbose_name = "Contador Sequencial"
        verbose_name_plural = "Contadores Sequenciais"


class ContasAPagar(models.Model):
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, verbose_name="Fornecedor")
    empresa_pagadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa Pagadora")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name="Banco de Pagamento")
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    vencimento = models.DateField(verbose_name="Vencimento")
    nota = models.CharField(max_length=50, unique=True, verbose_name="Nº da Nota Fiscal")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    conta_contabil = models.CharField(max_length=50, blank=True, verbose_name="Conta Contábil")
    status = models.CharField(max_length=15, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE', verbose_name="Status")
    data_baixa = models.DateField(null=True, blank=True, verbose_name="Data de Baixa/Pagamento")
    usuario_baixa = models.ForeignKey(UsuarioCustomizado, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário da Baixa")

    def status_visual(self):
        hoje = date.today()
        cor_texto = 'white'
        if self.status == 'PAGO':
            cor, texto = '#28a745', 'PAGO'
        elif self.status == 'CANCELADO':
            cor, texto = '#6c757d', 'CANCELADO'
        else:
            if self.vencimento < hoje:
                dias = (hoje - self.vencimento).days
                cor, texto = '#dc3545', f'VENCIDO ({dias} dias)'
            elif self.vencimento == hoje:
                cor, texto, cor_texto = '#ffc107', 'VENCE HOJE', 'black'
            else:
                cor, texto = '#17a2b8', 'A VENCER'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 8px; '
            'border-radius: 4px; font-weight: bold; white-space: nowrap;">{}</span>',
            cor, cor_texto, texto
        )

    status_visual.short_description = "Situação"
    status_visual.admin_order_field = 'vencimento'

    def save(self, request=None, *args, **kwargs):
        if not self.nota:
            contador, created = Sequencial.objects.get_or_create(prefixo='CP', defaults={'ultimo_numero': 0})
            contador.ultimo_numero += 1
            contador.save()
            self.nota = f"CP-{contador.ultimo_numero:05d}"
            if request:
                messages.success(request, f"SUCESSO! Conta a Pagar criada: {self.nota}")
        if self.status == 'PAGO' and not self.data_baixa:
            self.data_baixa = date.today()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Conta a Pagar"
        verbose_name_plural = "Contas a Pagar"


class ContasAReceber(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    empresa_prestadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa Prestadora")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name="Banco de Recebimento")
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    vencimento = models.DateField(verbose_name="Vencimento")
    nota = models.CharField(max_length=50, unique=True, verbose_name="Nº da Nota Fiscal")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    escala_horas = models.CharField(max_length=50, blank=True, verbose_name="Escala de Horas")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    status = models.CharField(max_length=15, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE', verbose_name="Status")
    data_baixa = models.DateField(null=True, blank=True, verbose_name="Data de Baixa/Recebimento")
    usuario_baixa = models.ForeignKey(UsuarioCustomizado, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário da Baixa")

    def status_visual(self):
        hoje = date.today()
        cor_texto = 'white'
        if self.status == 'PAGO':
            cor, texto = '#28a745', 'RECEBIDO'
        elif self.status == 'CANCELADO':
            cor, texto = '#6c757d', 'CANCELADO'
        else:
            if self.vencimento < hoje:
                dias = (hoje - self.vencimento).days
                cor, texto = '#dc3545', f'VENCIDO ({dias} dias)'
            elif self.vencimento == hoje:
                cor, texto, cor_texto = '#ffc107', 'VENCE HOJE', 'black'
            else:
                cor, texto = '#17a2b8', 'A VENCER'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 8px; '
            'border-radius: 4px; font-weight: bold; white-space: nowrap;">{}</span>',
            cor, cor_texto, texto
        )

    status_visual.short_description = "Situação"
    status_visual.admin_order_field = 'vencimento'

    def save(self, request=None, *args, **kwargs):
        if not self.nota:
            contador, created = Sequencial.objects.get_or_create(prefixo='CR', defaults={'ultimo_numero': 0})
            contador.ultimo_numero += 1
            contador.save()
            self.nota = f"CR-{contador.ultimo_numero:05d}"
            if request:
                messages.success(request, f"SUCESSO! Conta a Receber criada: {self.nota}")
        if self.status == 'PAGO' and not self.data_baixa:
            self.data_baixa = date.today()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Conta a Receber"
        verbose_name_plural = "Contas a Receber"


class BaseSaldo(models.Model):
    origem = models.CharField(max_length=10, verbose_name="Origem")
    id_origem = models.IntegerField(verbose_name="ID Original")
    nome = models.CharField(max_length=200, verbose_name="Nome (Forn/Cli)")
    empresa = models.CharField(max_length=200, verbose_name="Empresa")
    data_emissao = models.DateField(verbose_name="Emissão")
    banco = models.CharField(max_length=100, verbose_name="Banco")
    vencimento = models.DateField(verbose_name="Vencimento")
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


class GerarFixo(models.Model):
    class Meta:
        managed = False
        verbose_name = 'Gerar Fixo Mensal'
        verbose_name_plural = 'Gerar Fixos Mensais'


class Transferencia(models.Model):
    data = models.DateField(default=timezone.now, verbose_name="Data da Transferência")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    empresa = models.ForeignKey(
        'cadastros.Empresa', on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Empresa"
    )
    banco_origem = models.ForeignKey(
        'cadastros.Banco', related_name='transferencias_origem',
        on_delete=models.PROTECT, verbose_name="Banco de Origem (Saiu)"
    )
    banco_destino = models.ForeignKey(
        'cadastros.Banco', related_name='transferencias_destino',
        on_delete=models.PROTECT, verbose_name="Banco de Destino (Entrou)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_TRANSFERENCIA_CHOICES,
        default='DEFINITIVA',
        verbose_name="Classificação"
    )
    instrucao_retorno = models.TextField(
        blank=True, verbose_name="Instruções de Retorno",
        help_text="Preencha apenas para transferências temporárias."
    )
    data_prevista_retorno = models.DateField(
        null=True, blank=True,
        verbose_name="Data Prevista de Retorno",
        help_text="Obrigatório para transferências temporárias."
    )
    data_devolucao = models.DateField(
        null=True, blank=True,
        verbose_name="Data de Devolução Efetiva",
        help_text="Preenchida automaticamente ao marcar como Devolvida."
    )
    observacao = models.TextField(blank=True, verbose_name="Observações")
    criado_por = models.ForeignKey(
        'core.UsuarioCustomizado', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Criado por"
    )

    class Meta:
        verbose_name = "Transferência"
        verbose_name_plural = "Transferências"

    def __str__(self):
        return (
            f"{self.data.strftime('%d/%m/%Y')} | "
            f"{self.banco_origem} ➜ {self.banco_destino} "
            f"(R$ {self.valor}) [{self.get_status_display()}]"
        )

    def save(self, *args, **kwargs):
        is_new = not self.pk

        # Preenche data de devolução automaticamente
        if self.status == 'TEMP_DEVOLVIDA' and not self.data_devolucao:
            self.data_devolucao = date.today()

        super().save(*args, **kwargs)

        # Remove registros anteriores para recriar atualizados (cobre edições e cancelamentos)
        BaseSaldo.objects.filter(origem='TRF', id_origem=self.pk).delete()

        if self.status != 'CANCELADA':
            empresa_nome = self.empresa.nome if self.empresa else '-'
            usuario = self.criado_por.username if self.criado_por else 'sistema'

            # SAÍDA do banco de origem (valor negativo)
            BaseSaldo.objects.create(
                origem='TRF',
                id_origem=self.pk,
                nome=f"Transferência ➜ {self.banco_destino.nome}",
                empresa=empresa_nome,
                data_emissao=self.data,
                banco=self.banco_origem.nome,
                vencimento=self.data,
                valor=-self.valor,
                status='PAGO',
                data_baixa=self.data,
                usuario_baixa=usuario
            )
            # ENTRADA no banco de destino (valor positivo)
            BaseSaldo.objects.create(
                origem='TRF',
                id_origem=self.pk,
                nome=f"Transferência ← {self.banco_origem.nome}",
                empresa=empresa_nome,
                data_emissao=self.data,
                banco=self.banco_destino.nome,
                vencimento=self.data,
                valor=self.valor,
                status='PAGO',
                data_baixa=self.data,
                usuario_baixa=usuario
            )

    def delete(self, *args, **kwargs):
        BaseSaldo.objects.filter(origem='TRF', id_origem=self.pk).delete()
        super().delete(*args, **kwargs)