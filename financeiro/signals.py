# financeiro/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ContasAPagar, ContasAReceber, BaseSaldo

# --- 1. AUTOMAÇÃO CONTAS A PAGAR (CP) ---
@receiver(post_save, sender=ContasAPagar)
def atualizar_saldo_cp(sender, instance, **kwargs):
    # Só gera saldo se estiver PAGO
    if instance.status == 'PAGO':
        # Cria ou Atualiza a linha na BaseSaldo
        BaseSaldo.objects.update_or_create(
            origem='CP',           # Marca que veio do CP
            id_origem=instance.id, # Guarda o ID original para poder editar depois
            defaults={
                'nome': str(instance.fornecedor),
                'empresa': str(instance.empresa_pagadora),
                'data_emissao': instance.data_emissao,
                'banco': str(instance.banco),
                'vencimento': instance.vencimento,
                'valor': instance.valor * -1, # NEGATIVO (Saída de dinheiro)
                'status': instance.status,
                'data_baixa': instance.data_baixa,
                # Pega o usuário se existir, senão coloca 'Sistema'
                'usuario_baixa': str(instance.usuario_baixa) if instance.usuario_baixa else 'Sistema'
            }
        )
    else:
        # Se você desmarcar o PAGO (voltar para Pendente), removemos do saldo
        BaseSaldo.objects.filter(origem='CP', id_origem=instance.id).delete()

# --- 2. AUTOMAÇÃO CONTAS A RECEBER (CR) ---
@receiver(post_save, sender=ContasAReceber)
def atualizar_saldo_cr(sender, instance, **kwargs):
    if instance.status == 'PAGO':
        BaseSaldo.objects.update_or_create(
            origem='CR',
            id_origem=instance.id,
            defaults={
                'nome': str(instance.cliente),
                'empresa': str(instance.empresa_prestadora),
                'data_emissao': instance.data_emissao,
                'banco': str(instance.banco),
                'vencimento': instance.vencimento,
                'valor': instance.valor, # POSITIVO (Entrada de dinheiro)
                'status': instance.status,
                'data_baixa': instance.data_baixa,
                'usuario_baixa': str(instance.usuario_baixa) if instance.usuario_baixa else 'Sistema'
            }
        )
    else:
        # Se deixou de ser PAGO, remove
        BaseSaldo.objects.filter(origem='CR', id_origem=instance.id).delete()

# --- 3. LIMPEZA (Se você apagar a conta original, apaga o saldo) ---
@receiver(post_delete, sender=ContasAPagar)
def remove_saldo_cp(sender, instance, **kwargs):
    BaseSaldo.objects.filter(origem='CP', id_origem=instance.id).delete()

@receiver(post_delete, sender=ContasAReceber)
def remove_saldo_cr(sender, instance, **kwargs):
    BaseSaldo.objects.filter(origem='CR', id_origem=instance.id).delete()