# workflow/models.py
from django.db import models
from django.utils import timezone
from core.models import UsuarioCustomizado
from cadastros.models import Fornecedor, Empresa, Banco, Tomador, Filial, MotivoAusencia, Colaborador

STATUS_WORKFLOW = [
    ('AGUARDANDO_COMERCIAL', 'Aguardando Comercial'),
    ('AGUARDANDO_ADM', 'Aguardando Administrativo'),
    ('AGUARDANDO_RH', 'Aguardando RH'),
    ('AGUARDANDO_FIN', 'Aguardando Financeiro'),
    ('DIRECIONADO_OP', 'Direcionado ao Operador'),
    ('PAGO', 'Pago / Finalizado'),
    ('CONFERIDO', 'Conferido'),
    ('CANCELADO', 'Cancelado'),
]

TIPO_LANCAMENTO_CHOICES = [
    ('CAIXINHA', 'Caixinha'),
    ('SOLICITACAO', 'Solicitação'),
    ('EXTRA', 'Extra'),
]

FORMA_PAGTO_CHOICES = [
    ('PIX', 'Pix'),
    ('BANCO', 'Transferência Bancária'),
    ('DINHEIRO', 'Dinheiro')
]


class Despesa(models.Model):
    tipo_lancamento = models.CharField(max_length=20, choices=TIPO_LANCAMENTO_CHOICES, default='CAIXINHA',
                                       verbose_name="Tipo")
    data_despesa = models.DateField(default=timezone.now, verbose_name="Data da Despesa")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, verbose_name="Despesa")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    solicitante = models.ForeignKey(UsuarioCustomizado, on_delete=models.PROTECT, related_name='solicitacoes',
                                    verbose_name="Solicitante")
    status = models.CharField(max_length=20, choices=STATUS_WORKFLOW, default='AGUARDANDO_RH',
                              verbose_name="Status Atual")

    # Campos específicos
    # AJUSTE: Organização automática por Ano e Mês
    comprovante = models.FileField(upload_to='comprovantes/%Y/%m/', null=True, blank=True,
                                   verbose_name="Comprovante (Upload)")

    inicio_cobertura = models.DateField(null=True, blank=True, verbose_name="Cob Início")
    fim_cobertura = models.DateField(null=True, blank=True, verbose_name="Cob Fim")
    dias_cobertura = models.TextField(blank=True, verbose_name="Dias de Cobertura",
                                      help_text="Dias de cobertura!")
    tomador = models.ForeignKey(Tomador, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tomador")
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Filial")
    motivo_ausencia = models.ForeignKey(MotivoAusencia, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name="Motivo")
    colaborador_faltou = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='faltas_workflow', verbose_name="Quem Faltou")

    # DEFINIÇÃO DE PAGAMENTO (ADMINISTRATIVO)
    nome_cobriu = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nome de Quem Cobriu")
    forma_pagamento = models.CharField(max_length=10, choices=FORMA_PAGTO_CHOICES, blank=True, null=True,
                                       verbose_name="Forma Pagamento")
    dados_bancarios_pagto = models.TextField(blank=True, null=True, verbose_name="Dados para Depósito")

    # Aprovação e Execução
    empresa_pagadora = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True,
                                         verbose_name="Empresa Pagadora")
    banco_pagador = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name="Banco Pagador")
    operador = models.ForeignKey(UsuarioCustomizado, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='tarefas_operador', verbose_name="Selecione o Operador")
    motivo_cancelamento = models.TextField(blank=True, verbose_name="Motivo do Cancelamento")
    justificativa_retorno = models.TextField(blank=True, verbose_name="Justificativa / Questionamento")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora da Solicitação", null=True)
    data_ultima_alteracao = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.nome_cobriu: self.nome_cobriu = self.nome_cobriu.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.id} - {self.valor}"

    class Meta:
        verbose_name = "Workflow de Despesa"
        verbose_name_plural = "Workflow de Despesas"
        permissions = [
            ('view_cloudinary_storage', 'Pode acessar armazenamento Cloudinary'),
        ]


STATUS_COM_SLA = [
    ('AGUARDANDO_COMERCIAL', 'Aguardando Comercial'),
    ('AGUARDANDO_ADM', 'Aguardando Administrativo'),
    ('AGUARDANDO_RH', 'Aguardando RH'),
    ('AGUARDANDO_FIN', 'Aguardando Financeiro'),
    ('DIRECIONADO_OP', 'Direcionado ao Operador'),
]


class ConfiguracaoSLA(models.Model):
    status = models.CharField(
        max_length=30, choices=STATUS_COM_SLA, unique=True, verbose_name="Status"
    )
    prazo_dias = models.PositiveIntegerField(
        default=0, verbose_name="Prazo (dias)",
        help_text="Parte em dias do prazo máximo permitido neste status."
    )
    prazo_horas = models.PositiveIntegerField(
        default=0, verbose_name="Prazo (horas)",
        help_text="Parte em horas (0-23) do prazo máximo permitido neste status."
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    @property
    def total_horas(self):
        return self.prazo_dias * 24 + self.prazo_horas

    def __str__(self):
        partes = []
        if self.prazo_dias:
            partes.append(f"{self.prazo_dias}d")
        if self.prazo_horas:
            partes.append(f"{self.prazo_horas}h")
        prazo_str = " ".join(partes) or "0h"
        return f"{self.get_status_display()} — {prazo_str}"

    class Meta:
        verbose_name = "Configuração de SLA"
        verbose_name_plural = "Configurações de SLA"
        ordering = ['status']


class LogWorkflow(models.Model):
    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name='logs')
    usuario = models.ForeignKey(UsuarioCustomizado, on_delete=models.PROTECT)
    perfil_usuario = models.CharField(max_length=50)
    acao = models.CharField(max_length=100)
    data_hora = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)