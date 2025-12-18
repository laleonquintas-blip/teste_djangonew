# financeiro/views.py
from django.http import JsonResponse
from cadastros.models import Fornecedor
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def get_fornecedor_info(request):
    fornecedor_id = request.GET.get('id')
    try:
        fornecedor = Fornecedor.objects.get(id=fornecedor_id)
        # Retorna se é SOLICITACAO (Letra A) ou CAIXINHA (Outros)
        tipo = 'SOLICITACAO' if fornecedor.letra_acesso == 'A' else 'CAIXINHA'
        return JsonResponse({'tipo': tipo})
    except Fornecedor.DoesNotExist:
        return JsonResponse({'tipo': 'DESCONHECIDO'}, status=404)