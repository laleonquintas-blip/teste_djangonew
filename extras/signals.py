# extras/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import LancamentoExtra
from financeiro.models import ContasAReceber
from workflow.models import Despesa
from cadastros.models import Fornecedor, Cliente


@receiver(post_save, sender=LancamentoExtra)
def automacao_extras(sender, instance, created, **kwargs):
    # 1. CLIENTE GENÉRICO
    cliente_padrao, _ = Cliente.objects.get_or_create(
        razao_social="CLIENTE EXTRA (AUTO)",
        defaults={
            'cnpj_cpf': '00000000000',
            'dia_vencimento': 1,
            'valor_contrato': 0.00,
            'ativo': True,
            'tipo': 'EVENTUAL'
        }
    )

    # 2. CONTAS A RECEBER
    novo_cr, cr_created = ContasAReceber.objects.update_or_create(
        nota=f"EXTRA-{instance.nota_fiscal}",
        defaults={
            'cliente': cliente_padrao,
            'empresa_prestadora': instance.empresa_prestadora,
            'banco': instance.banco_recebimento,
            'data_emissao': instance.data_emissao,
            'vencimento': instance.data_vencimento,
            'valor': instance.valor_recebimento,
            'observacoes': f"Tipo: {instance.tipo_fixo} | NF: {instance.nota_fiscal}",
            'status': 'PENDENTE'
        }
    )

    # 3. WORKFLOW (DESPESA)
    fornecedor_extra, _ = Fornecedor.objects.get_or_create(
        razao_social="LANÇAMENTOS EXTRAS (AUTO)",
        defaults={'cnpj_cpf': '00000000000000'}
    )

    if instance.workflow_criado:
        novo_wf = instance.workflow_criado
        novo_wf.observacoes = f"Origem: {instance.tipo_fixo} | NF: {instance.nota_fiscal}"
        novo_wf.data_despesa = instance.data_emissao
        novo_wf.save()
    else:
        # CRIAÇÃO DO WORKFLOW
        # Nota: Os campos de pagamento (nome_cobriu, etc) nascem vazios
        # para o Administrativo preencher depois.
        novo_wf = Despesa.objects.create(
            tipo_lancamento='EXTRA',
            solicitante=instance.administrativo,
            fornecedor=fornecedor_extra,
            valor=0.00,
            status='AGUARDANDO_ADM',
            observacoes=f"Origem: {instance.tipo_fixo} | NF: {instance.nota_fiscal}",
            data_despesa=instance.data_emissao,

            # Copiando apenas os dados operacionais
            inicio_cobertura=instance.inicio_cobertura,
            fim_cobertura=instance.fim_cobertura,
            tomador=instance.tomador,
            filial=instance.filial,
            motivo_ausencia=instance.motivo_ausencia,
            colaborador_faltou=instance.colaborador_faltou
        )

    # 4. SALVAR VÍNCULOS
    LancamentoExtra.objects.filter(pk=instance.pk).update(
        conta_receber_criada=novo_cr,
        workflow_criado=novo_wf
    )


@receiver(post_delete, sender=LancamentoExtra)
def remover_vinculos_extra(sender, instance, **kwargs):
    if instance.conta_receber_criada:
        instance.conta_receber_criada.delete()

    if instance.workflow_criado:
        instance.workflow_criado.delete()