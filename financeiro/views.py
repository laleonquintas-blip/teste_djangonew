# financeiro/views.py

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages, admin
from django.db.models import Sum, Count
from django.utils import timezone

from cadastros.models import Fornecedor, Banco, Cliente, Empresa
from financeiro.models import ContasAPagar, ContasAReceber, Transferencia


@staff_member_required
def get_fornecedor_info(request):
    fornecedor_id = request.GET.get('id')
    try:
        fornecedor = Fornecedor.objects.get(id=fornecedor_id)
        tipo = 'SOLICITACAO' if fornecedor.letra_acesso == 'A' else 'CAIXINHA'
        return JsonResponse({'tipo': tipo})
    except Fornecedor.DoesNotExist:
        return JsonResponse({'tipo': 'DESCONHECIDO'}, status=404)


@staff_member_required
@permission_required('financeiro.view_contasapagar', raise_exception=True)
def dashboard_financeiro(request):
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

    bancos = Banco.objects.exclude(nome__contains="(AUTO)")
    dados_bancos = []
    saldo_geral = 0

    for banco in bancos:
        total_entradas = ContasAReceber.objects.filter(
            banco=banco, status='PAGO', data_baixa__lte=data_referencia
        ).aggregate(total=Sum('valor'))['total'] or 0

        total_saidas = ContasAPagar.objects.filter(
            banco=banco, status='PAGO', data_baixa__lte=data_referencia
        ).aggregate(total=Sum('valor'))['total'] or 0

        transferencias_entrada = Transferencia.objects.filter(
            banco_destino=banco,
            data__lte=data_referencia
        ).exclude(status='CANCELADA').aggregate(total=Sum('valor'))['total'] or 0

        transferencias_saida = Transferencia.objects.filter(
            banco_origem=banco,
            data__lte=data_referencia
        ).exclude(status='CANCELADA').aggregate(total=Sum('valor'))['total'] or 0

        saldo_inicial = getattr(banco, 'saldo_inicial', 0) or 0
        saldo = saldo_inicial + total_entradas - total_saidas + transferencias_entrada - transferencias_saida
        saldo_geral += saldo

        dados_bancos.append({
            'nome': banco.nome,
            'entradas': total_entradas + transferencias_entrada,
            'saidas': total_saidas + transferencias_saida,
            'saldo': saldo
        })

    def calcular_resumo(Modelo):
        qs = Modelo.objects.filter(status='PENDENTE')
        vencidos = qs.filter(vencimento__lt=data_referencia).aggregate(qtd=Count('id'), valor=Sum('valor'))
        a_vencer = qs.filter(vencimento__gte=data_referencia).aggregate(qtd=Count('id'), valor=Sum('valor'))
        return {
            'vencidos_qtd': vencidos['qtd'] or 0,
            'vencidos_valor': vencidos['valor'] or 0,
            'a_vencer_qtd': a_vencer['qtd'] or 0,
            'a_vencer_valor': a_vencer['valor'] or 0,
        }

    context = {
        'available_apps': admin.site.get_app_list(request),
        'dados_bancos': dados_bancos,
        'saldo_geral': saldo_geral,
        'cp': calcular_resumo(ContasAPagar),
        'cr': calcular_resumo(ContasAReceber),
        'site_header': 'Malupe Admin',
        'site_title': 'Malupe Admin',
        'filtro_atual': data_filtro,
        'data_referencia': data_referencia,
        'modo_tempo': modo_tempo,
    }
    return render(request, 'admin/financeiro/dashboard_gerencial.html', context)


@staff_member_required
def gerar_fixos_mensais(request):
    empresas = Empresa.objects.all()
    bancos = Banco.objects.all()
    clientes = Cliente.objects.filter(ativo=True)

    if request.method == 'POST':
        clientes_selecionados = request.POST.getlist('clientes_selecionados')
        erros = []
        gerados = 0

        for cliente_id in clientes_selecionados:
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                data_str = request.POST.get(f'data_gerar_{cliente_id}')
                empresa_id = request.POST.get(f'empresa_{cliente_id}')
                banco_id = request.POST.get(f'banco_{cliente_id}')

                if not data_str or not empresa_id or not banco_id:
                    erros.append(f"{cliente.razao_social}: preencha empresa, banco e data.")
                    continue

                vencimento = datetime.strptime(data_str, '%Y-%m-%d').date()
                empresa = Empresa.objects.get(id=empresa_id)
                banco = Banco.objects.get(id=banco_id)

                ja_existe = ContasAReceber.objects.filter(
                    cliente=cliente, vencimento=vencimento
                ).exists()

                if ja_existe:
                    erros.append(f"{cliente.razao_social}: já existe CR para {vencimento.strftime('%d/%m/%Y')}.")
                    continue

                cr = ContasAReceber(
                    cliente=cliente,
                    empresa_prestadora=empresa,
                    banco=banco,
                    data_emissao=date.today(),
                    vencimento=vencimento,
                    valor=cliente.valor_contrato,
                    observacoes="Fixo mensal gerado automaticamente.",
                    status='PENDENTE',
                )
                cr.save(request=request)
                gerados += 1

            except Exception as e:
                erros.append(f"Erro no cliente ID {cliente_id}: {str(e)}")

        if gerados:
            messages.success(request, f"✅ {gerados} Conta(s) a Receber gerada(s) com sucesso!")
        for erro in erros:
            messages.warning(request, f"⚠️ {erro}")

        return redirect('gerar_fixos_mensais')

    context = {
        'clientes': clientes,
        'empresas': empresas,
        'bancos': bancos,
        'available_apps': admin.site.get_app_list(request),
        'site_header': 'Malupe Admin',
        'site_title': 'Malupe Admin',
    }
    return render(request, 'admin/financeiro/gerar_fixos.html', context)


@staff_member_required
def ajustar_saldos_bancos(request):
    if not request.user.is_superuser:
        messages.error(request, "⚠️ Acesso negado. Apenas o usuário Master pode ajustar os saldos iniciais.")
        return redirect('admin:index')

    bancos = Banco.objects.all()

    if request.method == 'POST':
        try:
            for banco in bancos:
                valor_str = request.POST.get(f'saldo_inicial_{banco.id}')
                if valor_str is not None:
                    # Remove separador de milhar (ponto) e converte vírgula decimal para ponto
                    valor_str = valor_str.strip().replace('.', '').replace(',', '.')
                    try:
                        banco.saldo_inicial = Decimal(valor_str or '0')
                    except InvalidOperation:
                        banco.saldo_inicial = Decimal('0')
                    banco.save()

            messages.success(request, "✅ Saldos iniciais atualizados com sucesso!")
            return redirect('ajustar_saldos')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar saldos: {e}")

    context = {
        'bancos': bancos,
        'site_header': 'Malupe Admin',
        'site_title': 'Malupe Admin',
        'available_apps': admin.site.get_app_list(request),
    }
    return render(request, 'admin/financeiro/ajustar_saldos.html', context)