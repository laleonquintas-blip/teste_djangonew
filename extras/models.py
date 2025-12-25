from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from financeiro.models import ContasAReceber
from workflow.models import Despesa
from cadastros.models import Tomador, Filial, MotivoAusencia, Colaborador, Banco, Empresa


class LancamentoExtra(models.Model):
    # --- 1. DADOS DE EMISSÃO ---
    nota_fiscal = models.CharField("Nota Fiscal", max_length=50, blank=True, editable=False)
    data_emissao = models.DateField("Data da Emissão", default=timezone.now, editable=False)
    data_vencimento = models.DateField("Data de Vencimento")
    tipo_fixo = models.CharField("Tipo", max_length=50, default="Extra", editable=False)

    valor_recebimento = models.DecimalField(
        "Valor (Receita)", max_digits=10, decimal_places=2
    )

    # --- 2. DADOS FINANCEIROS ---
    empresa_prestadora = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        verbose_name="Empresa Prestadora",
        help_text="Empresa do Grupo que receberá o valor",
        limit_choices_to=~Q(nome__contains="(AUTO)")
    )

    banco_recebimento = models.ForeignKey(
        Banco,
        on_delete=models.PROTECT,
        verbose_name="Banco de Recebimento",
        limit_choices_to=~Q(nome__contains="(AUTO)")
    )

    # --- 3. RESPONSÁVEL ---
    administrativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Responsável Administrativo (Aprovador)",
        limit_choices_to={'groups__name': 'Administrativo'},
        related_name='extras_solicitados'
    )

    # --- 4. DETALHES SOLICITAÇÃO ---
    inicio_cobertura = models.DateField("Início Cobertura", null=True, blank=True)
    fim_cobertura = models.DateField("Fim Cobertura", null=True, blank=True)
    tomador = models.ForeignKey(Tomador, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tomador")
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Filial")

    # AJUSTE 1: Verbose name mudado para "Motivo"
    motivo_ausencia = models.ForeignKey(MotivoAusencia, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name="Motivo")

    colaborador_faltou = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True,
                                           verbose_name="Colaborador que Faltou")

    # AJUSTE 2: CAMPOS DE PAGAMENTO REMOVIDOS DAQUI
    # (nome_cobriu, forma_pagamento, dados_bancarios foram retirados)

    # --- 5. VÍNCULOS ---
    conta_receber_criada = models.OneToOneField(ContasAReceber, on_delete=models.SET_NULL, null=True, blank=True,
                                                editable=False)
    workflow_criado = models.OneToOneField(Despesa, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
                                           related_name='lancamentoextra')

    class Meta:
        verbose_name = "Lançamento de Extra"
        verbose_name_plural = "Lançamentos de Extras"

    def __str__(self):
        return f"{self.nota_fiscal} - R$ {self.valor_recebimento}"

    def save(self, *args, **kwargs):
        if not self.nota_fiscal:
            proximo_id = LancamentoExtra.objects.count() + 1
            self.nota_fiscal = f"LE{proximo_id:04d}"
        super().save(*args, **kwargs)