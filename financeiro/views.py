# financeiro/views.py

from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib import admin

from cadastros.models import Fornecedor, Banco
from financeiro.models import ContasAPagar, ContasAReceber


# --- 1. FUNÇÃO QUE ESTAVA FALTANDO (Traz informações do Fornecedor) ---
@staff_member_required
def get_fornecedor_info(request):
    fornecedor_id = request.GET.get('id')
    try:
        fornecedor = Fornecedor.objects.get(id=fornecedor_id)
        # Verifica se o fornecedor tem letra de acesso 'A' (Solicitação) ou 'B' (Caixinha)
        # Ajuste a lógica conforme seu modelo real, aqui assumi 'A' e 'B' baseado em conversas anteriores
        tipo = 'SOLICITACAO' if fornecedor.letra_acesso == 'A' else 'CAIXINHA'
        return JsonResponse({'tipo': tipo})
    except Fornecedor.DoesNotExist:
        return JsonResponse({'tipo': 'DESCONHECIDO'}, status=404)
    except Exception as e:
        return JsonResponse({'tipo': 'ERRO', 'msg': str(e)}, status=500)


# --- 2. DASHBOARD FINANCEIRO (Com Máquina do Tempo) ---
@staff_member_required
def dashboard_financeiro(request):
    # --- DEFINIR A DATA DE CORTE ---
    data_filtro = request.GET.get('filtro_vencimento')

    if data_filtro:
        try:
            data_referencia = datetime.strptime(data_filtro, '%Y-%m-%d').date()
            modo_tempo = 'HISTORICO'
        except ValueError:
            data_referencia = timezone.now().date()
            modo_tempo = 'ATUAL'
    else:
        data_referencia = timezone.now().date()
        modo_tempo = 'ATUAL'

    # --- CÁLCULO DE SALDOS (RETROSPECTIVO) ---
    bancos = Banco.objects.exclude(nome__contains="(AUTO)")
    dados_bancos = []
    saldo_geral = 0

    for banco in bancos:
        # Soma entradas pagas ATÉ a data escolhida (data_baixa)
        total_entradas = ContasAReceber.objects.filter(
            banco=banco,
            status='PAGO',
            data_baixa__lte=data_referencia
        ).aggregate(total=Sum('valor'))['total'] or 0

        # Soma saídas pagas ATÉ a data escolhida (data_baixa)
        total_saidas = ContasAPagar.objects.filter(
            banco=banco,
            status='PAGO',
            data_baixa__lte=data_referencia
        ).aggregate(total=Sum('valor'))['total'] or 0

        saldo = total_entradas - total_saidas
        saldo_geral += saldo

        dados_bancos.append({
            'nome': banco.nome,
            'entradas': total_entradas,
            'saidas': total_saidas,
            'saldo': saldo
        })

    # --- CÁLCULO DE TÍTULOS (CENÁRIO DA DATA) ---
    def calcular_resumo(Modelo):
        qs = Modelo.objects.filter(status='PENDENTE')

        # Vencidos ANTES da data de referência
        vencidos = qs.filter(vencimento__lt=data_referencia).aggregate(
            qtd=Count('id'), valor=Sum('valor')
        )

        # A Vencer A PARTIR da data de referência
        a_vencer = qs.filter(vencimento__gte=data_referencia).aggregate(
            qtd=Count('id'), valor=Sum('valor')
        )

        return {
            'vencidos_qtd': vencidos['qtd'] or 0,
            'vencidos_valor': vencidos['valor'] or 0,
            'a_vencer_qtd': a_vencer['qtd'] or 0,
            'a_vencer_valor': a_vencer['valor'] or 0,
        }

    resumo_cp = calcular_resumo(ContasAPagar)
    resumo_cr = calcular_resumo(ContasAReceber)

    # --- CONTEXTO FINAL ---
    available_apps = admin.site.get_app_list(request)

    context = {
        'available_apps': available_apps,
        'dados_bancos': dados_bancos,
        'saldo_geral': saldo_geral,
        'cp': resumo_cp,
        'cr': resumo_cr,
        'site_header': 'Malupe Admin',
        'site_title': 'Malupe Admin',
        'filtro_atual': data_filtro,
        'data_referencia': data_referencia,
        'modo_tempo': modo_tempo,
    }

    return render(request, 'admin/dashboard_custom.html', context)