# financeiro/models.py

from django.db import models, transaction
from django.utils import timezone
from django.contrib import messages
from datetime import date
from django.utils.html import format_html
from cadastros.models import Cliente, Fornecedor, Empresa, Banco, TipoServico, PlanoDeContas
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
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Fornecedor")
    empresa_pagadora = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name="Empresa Pagadora")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name="Banco de Pagamento")
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    vencimento = models.DateField(verbose_name="Vencimento")
    nota = models.CharField(max_length=50, unique=True, verbose_name="Nº da Nota Fiscal")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    plano_de_contas = models.ForeignKey(
        PlanoDeContas, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Plano de Contas"
    )
    status = models.CharField(max_length=15, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE', verbose_name="Status")
    responsavel_pagamento = models.ForeignKey(
        UsuarioCustomizado, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contas_responsavel',
        verbose_name="Responsável pelo Pagamento"
    )
    supervisor = models.ForeignKey(
        UsuarioCustomizado, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contas_supervisor',
        verbose_name="Supervisor"
    )
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
        with transaction.atomic():
            self._save_logic(request, *args, **kwargs)

    def _save_logic(self, request=None, *args, **kwargs):
        if not self.nota:
            contador, created = Sequencial.objects.get_or_create(prefixo='CP', defaults={'ultimo_numero': 0})
            contador.ultimo_numero += 1
            contador.save()
            self.nota = f"CP-{contador.ultimo_numero:05d}"
            if request:
                messages.success(request, f"SUCESSO! Conta a Pagar criada: {self.nota}")
        if self.status == 'PAGO' and not self.data_baixa:
            self.data_baixa = date.today()
        # Detecta mudança de status para comparação
        status_anterior = None
        if self.pk:
            try:
                status_anterior = ContasAPagar.objects.get(pk=self.pk).status
            except ContasAPagar.DoesNotExist:
                pass

        # Crédito automático no saldo do supervisor quando CP é pago
        credito_pendente = None
        if self.status == 'PAGO' and self.supervisor_id and status_anterior != 'PAGO':
            saldo_sup = SaldoSupervisor.objects.filter(
                supervisor_id=self.supervisor_id, status='ABERTO'
            ).order_by('-data_inicio').first()
            if not saldo_sup:
                supervisor = UsuarioCustomizado.objects.get(pk=self.supervisor_id)
                saldo_sup = SaldoSupervisor.objects.create(supervisor=supervisor)
            # F() garante atualização atômica (evita race condition em multithread)
            SaldoSupervisor.objects.filter(pk=saldo_sup.pk).update(
                saldo_disponivel=models.F('saldo_disponivel') + self.valor
            )
            saldo_sup.refresh_from_db()
            credito_pendente = saldo_sup

        # Estorno do crédito quando CP sai do status PAGO (volta p/ PENDENTE ou similar)
        if status_anterior == 'PAGO' and self.status not in ('PAGO', 'CANCELADO') and self.supervisor_id:
            mov = MovimentacaoSupervisor.objects.filter(referencia_cp=self).first()
            if mov:
                saldo_sup = mov.saldo_supervisor
                SaldoSupervisor.objects.filter(pk=saldo_sup.pk).update(
                    saldo_disponivel=models.F('saldo_disponivel') - mov.valor
                )
                mov.delete()
                # Se o ciclo ficou sem movimentações, remove para não bloquear novo crédito
                if not saldo_sup.movimentacoes.exists():
                    saldo_sup.delete()

        # Cancelamento: cancela o SaldoSupervisor vinculado se não tiver débitos
        if self.status == 'CANCELADO' and self.supervisor_id and status_anterior not in (None, 'CANCELADO'):
            # Usa sempre o FK direto — nunca fallback por supervisor (risco de atingir ciclo errado)
            mov = MovimentacaoSupervisor.objects.filter(referencia_cp=self).first()
            if mov:
                saldo_sup = mov.saldo_supervisor
                tem_debitos = saldo_sup.movimentacoes.filter(tipo='DEBITO').exists()
                if not tem_debitos:
                    saldo_sup.movimentacoes.all().delete()
                    saldo_sup.saldo_disponivel = 0
                    saldo_sup.status = 'CANCELADO'
                    saldo_sup.save()

        super().save(*args, **kwargs)

        # Cria a movimentação de crédito APÓS o super().save() (self.pk garantido)
        if credito_pendente:
            MovimentacaoSupervisor.objects.create(
                saldo_supervisor=credito_pendente,
                tipo='CREDITO',
                valor=self.valor,
                descricao=f"CP {self.nota} — {self.fornecedor}",
                referencia_cp=self,
            )

    def delete(self, *args, **kwargs):
        # Estorna o crédito no saldo do supervisor ao excluir um CP pago com supervisor
        if self.supervisor_id:
            mov = MovimentacaoSupervisor.objects.filter(referencia_cp=self).first()
            if mov:
                saldo_sup = mov.saldo_supervisor
                if saldo_sup.movimentacoes.filter(tipo='DEBITO').exists():
                    raise ValueError(
                        f"Não é possível excluir este lançamento: o saldo do supervisor "
                        f"{saldo_sup.supervisor.first_name} ({saldo_sup.numero}) "
                        f"já possui utilizações registradas."
                    )
                saldo_sup.saldo_disponivel -= mov.valor
                saldo_sup.save()
                mov.delete()
                if not saldo_sup.movimentacoes.exists():
                    saldo_sup.delete()
            else:
                # Movimentação já foi removida (ex: CP voltou p/ PENDENTE antes de ser excluído)
                # Limpa SS órfão com saldo zero e sem débitos vinculado a este supervisor
                ss_orfao = SaldoSupervisor.objects.filter(
                    supervisor_id=self.supervisor_id,
                    status='ABERTO',
                    saldo_disponivel=0,
                ).filter(movimentacoes__isnull=True).first()
                if ss_orfao:
                    ss_orfao.delete()
        super().delete(*args, **kwargs)

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


class SaldoSupervisor(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('FECHADO', 'Fechado'),
        ('CANCELADO', 'Cancelado'),
    ]
    numero = models.CharField(max_length=12, unique=True, blank=True, verbose_name="Nº")
    supervisor = models.ForeignKey(
        UsuarioCustomizado, on_delete=models.PROTECT,
        related_name='saldos_supervisor', verbose_name="Supervisor"
    )
    saldo_disponivel = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Saldo Disponível")
    data_inicio = models.DateField(default=date.today, verbose_name="Data de Início")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTO', verbose_name="Status")
    fechado_por = models.ForeignKey(
        UsuarioCustomizado, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ciclos_fechados', verbose_name="Fechado por"
    )
    data_fechamento = models.DateTimeField(null=True, blank=True, verbose_name="Data do Fechamento")
    observacao_fechamento = models.TextField(blank=True, verbose_name="Observações do Fechamento")

    class Meta:
        verbose_name = "Saldo Supervisor"
        verbose_name_plural = "Saldo Supervisores"
        ordering = ['-data_inicio']

    def save(self, *args, **kwargs):
        if not self.pk:
            if SaldoSupervisor.objects.filter(supervisor=self.supervisor, status='ABERTO').exists():
                nome = self.supervisor.first_name.strip() or self.supervisor.username
                raise ValueError(f"Já existe um saldo aberto para {nome}. Feche o ciclo atual antes de criar um novo.")
        if not self.numero:
            ultimo = SaldoSupervisor.objects.order_by('-id').first()
            proximo = (ultimo.id + 1) if ultimo else 1
            self.numero = f"SS-{proximo:05d}"
        super().save(*args, **kwargs)

    @property
    def utilizacao(self):
        return self.movimentacoes.filter(tipo='DEBITO').aggregate(
            total=models.Sum('valor')
        )['total'] or 0

    @property
    def saldo(self):
        return self.saldo_disponivel - self.utilizacao

    def __str__(self):
        nome = self.supervisor.first_name.strip() or self.supervisor.username
        return f"{nome} — {self.data_inicio.strftime('%d/%m/%Y')} ({self.get_status_display()})"


class MovimentacaoSupervisor(models.Model):
    TIPO_CHOICES = [
        ('CREDITO', 'Crédito (Saldo)'),
        ('DEBITO', 'Débito (Utilização)'),
    ]
    saldo_supervisor = models.ForeignKey(
        SaldoSupervisor, on_delete=models.PROTECT,
        related_name='movimentacoes', verbose_name="Saldo"
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    descricao = models.CharField(max_length=200, verbose_name="Descrição")
    data = models.DateField(auto_now_add=True, verbose_name="Data")
    referencia_cp = models.ForeignKey(
        'ContasAPagar', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Ref. Contas a Pagar"
    )
    referencia_despesa_id = models.IntegerField(null=True, blank=True, verbose_name="Ref. Despesa Workflow (ID)")

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data', '-id']

    def __str__(self):
        nome = self.saldo_supervisor.supervisor.first_name.strip() or self.saldo_supervisor.supervisor.username
        return f"{self.get_tipo_display()} R$ {self.valor} — {nome}"