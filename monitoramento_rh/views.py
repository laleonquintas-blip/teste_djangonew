from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import ColaboradorInformal, ItemPagamento


@staff_member_required
def api_colaboradores_folha(request):
    folha_id = request.GET.get('folha_id')
    if not folha_id:
        return JsonResponse({'colaboradores': []})

    colaboradores = ColaboradorInformal.objects.filter(
        folha_id=folha_id, ativo=True
    ).select_related('filial').order_by('banco', 'nome')

    result = []
    for c in colaboradores:
        ultimo_valor = (
            ItemPagamento.objects
            .filter(colaborador=c, pagamento__status='PAGA')
            .order_by('-pagamento__data_fim')
            .values_list('valor_atual', flat=True)
            .first()
        )
        result.append({
            'nome':          c.nome,
            'cpf':           c.cpf,
            'filial':        str(c.filial),
            'banco':         c.banco,
            'agencia':       c.agencia,
            'conta':         c.conta,
            'valor_anterior': str(ultimo_valor) if ultimo_valor is not None else None,
            'valor_atual':   str(c.valor_padrao),
        })

    return JsonResponse({'colaboradores': result})
