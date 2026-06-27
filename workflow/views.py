from datetime import datetime
from collections import Counter
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F


@staff_member_required
def relatorio_coberturas(request):
    from workflow.models import Despesa
    from cadastros.models import Colaborador, MotivoAusencia

    DIAS_SEMANA = {
        1: 'Domingo',
        2: 'Segunda-feira',
        3: 'Terça-feira',
        4: 'Quarta-feira',
        5: 'Quinta-feira',
        6: 'Sexta-feira',
        7: 'Sábado',
    }

    qs = Despesa.objects.filter(
        status='PAGO',
        fornecedor__plano_de_contas__nome='Cobertura Falta',
    )

    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    colaborador_id = request.GET.get('colaborador', '')
    motivo_id = request.GET.get('motivo', '')

    if data_inicio:
        qs = qs.filter(data_despesa__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_despesa__lte=data_fim)
    if colaborador_id:
        qs = qs.filter(colaborador_faltou__id=colaborador_id)
    if motivo_id:
        qs = qs.filter(motivo_ausencia__id=motivo_id)

    total_ocorrencias = qs.count()
    total_gasto = qs.aggregate(total=Sum('valor'))['total'] or 0

    ranking_colaboradores = (
        qs.filter(colaborador_faltou__isnull=False)
        .values(
            collab_id=F('colaborador_faltou__id'),
            nome=F('colaborador_faltou__nome'),
        )
        .annotate(qtd=Count('id'), valor_total=Sum('valor'))
        .order_by('-qtd')
    )

    ranking_motivos = (
        qs.filter(motivo_ausencia__isnull=False)
        .values(
            motivo_id_val=F('motivo_ausencia__id'),
            motivo=F('motivo_ausencia__nome'),
        )
        .annotate(qtd=Count('id'))
        .order_by('-qtd')
    )

    sem_motivo = qs.filter(motivo_ausencia__isnull=True).count()

    motivos_com_pct = []
    for m in ranking_motivos:
        pct = round((m['qtd'] / total_ocorrencias * 100), 1) if total_ocorrencias else 0
        motivos_com_pct.append({**m, 'percentual': pct})

    if sem_motivo:
        pct = round((sem_motivo / total_ocorrencias * 100), 1) if total_ocorrencias else 0
        motivos_com_pct.append({
            'motivo_id_val': None,
            'motivo': 'Não informado',
            'qtd': sem_motivo,
            'percentual': pct,
        })

    from datetime import timedelta

    contagem_dias = Counter()
    for dias_cob, inicio, fim, data_desp in qs.values_list('dias_cobertura', 'inicio_cobertura', 'fim_cobertura', 'data_despesa'):
        datas = []

        if dias_cobertura := (dias_cob or '').strip():
            for parte in dias_cobertura.split(','):
                parte = parte.strip()
                if not parte:
                    continue
                try:
                    datas.append(datetime.strptime(parte, '%d-%m-%Y').date())
                except ValueError:
                    continue
        else:
            # Fallback: usa data_despesa
            if data_desp:
                datas = [data_desp]

        for dt in datas:
            nome_dia = DIAS_SEMANA[dt.isoweekday() % 7 + 1]
            contagem_dias[nome_dia] += 1

    dias_semana = [
        {'dia': dia, 'qtd': qtd}
        for dia, qtd in contagem_dias.most_common()
    ]

    colaborador_selecionado = None
    if colaborador_id:
        try:
            colaborador_selecionado = Colaborador.objects.get(id=colaborador_id).nome
        except Colaborador.DoesNotExist:
            pass

    motivo_selecionado = None
    if motivo_id:
        try:
            motivo_selecionado = MotivoAusencia.objects.get(id=motivo_id).nome
        except MotivoAusencia.DoesNotExist:
            pass

    context = {
        'title': 'Relatório de Coberturas de Falta',
        'total_gasto': total_gasto,
        'total_ocorrencias': total_ocorrencias,
        'ranking_colaboradores': ranking_colaboradores,
        'motivos': motivos_com_pct,
        'dias_semana': dias_semana,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'colaborador_id': colaborador_id,
        'colaborador_selecionado': colaborador_selecionado,
        'motivo_id': motivo_id,
        'motivo_selecionado': motivo_selecionado,
    }
    return render(request, 'admin/workflow/relatorio_coberturas.html', context)
