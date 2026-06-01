# extras/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import LancamentoExtra
from financeiro.models import ContasAReceber
from workflow.models import Despesa
from cadastros.models import Fornecedor, Cliente


@receiver(post_save, sender=LancamentoExtra)
def automacao_extras(sender, instance, created, **kwargs):
    # 1. CLIENTE — usa o Tomador se disponível, senão cai no genérico
    if instance.tomador:
        cnpj_tomador = f"TOM{instance.tomador.id:017d}"
        cliente_padrao, _ = Cliente.objects.get_or_create(
            cnpj_cpf=cnpj_tomador,
            defaults={
                'razao_social': instance.tomador.nome,
                'dia_vencimento': 1,
                'valor_contrato': 0.00,
                'ativo': True,
                'tipo': 'EVENTUAL'
            }
        )
        # Mantém o nome do tomador atualizado
        if cliente_padrao.razao_social != instance.tomador.nome:
            cliente_padrao.razao_social = instance.tomador.nome
            cliente_padrao.save()
    else:
        cliente_padrao, _ = Cliente.objects.get_or_create(
            cnpj_cpf='00000000000',
            defaults={
                'razao_social': 'CLIENTE EXTRA (AUTO)',
                'dia_vencimento': 1,
                'valor_contrato': 0.00,
                'ativo': True,
                'tipo': 'EVENTUAL'
            }
        )

    # 2. CONTAS A RECEBER — não sobrescreve o status se já estiver PAGO
    nota_cr = f"EXTRA-{instance.nota_fiscal}"
    novo_cr, cr_created = ContasAReceber.objects.get_or_create(
        nota=nota_cr,
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
    if not cr_created:
        # Atualiza apenas dados financeiros/operacionais, preserva status atual
        novo_cr.empresa_prestadora = instance.empresa_prestadora
        novo_cr.banco = instance.banco_recebimento
        novo_cr.vencimento = instance.data_vencimento
        novo_cr.valor = instance.valor_recebimento
        novo_cr.observacoes = f"Tipo: {instance.tipo_fixo} | NF: {instance.nota_fiscal}"
        novo_cr.save()

    # 3. WORKFLOW (DESPESA)
    # lookup por cnpj_cpf (campo unique) para evitar IntegrityError
    fornecedor_extra, _ = Fornecedor.objects.get_or_create(
        cnpj_cpf='00000000000000',
        defaults={'razao_social': 'LANÇAMENTOS EXTRAS (AUTO)'}
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