from datetime import datetime
from collections import Counter
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F
from django.utils import timezone as tz


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


@staff_member_required
def painel_sla(request):
    from .models import Despesa, ConfiguracaoSLA, LogWorkflow, STATUS_WORKFLOW
    from django import contrib
    import admin as django_admin

    # Carrega configurações de SLA ativas
    sla_map = {
        s.status: s.prazo_horas
        for s in ConfiguracaoSLA.objects.filter(ativo=True)
    }

    STATUS_FINAIS = {'PAGO', 'CONFERIDO', 'CANCELADO'}
    STATUS_LABELS = dict(STATUS_WORKFLOW)

    agora = tz.now()

    # Filtros
    filtro_tipo   = request.GET.get('tipo', '')
    filtro_status = request.GET.get('status', '')
    filtro_sla    = request.GET.get('sla', '')   # NO_PRAZO | A_VENCER | EM_ATRASO | FECHADO_ATRASO | FECHADO_OK
    filtro_de     = request.GET.get('data_de', '')
    filtro_ate    = request.GET.get('data_ate', '')

    qs = Despesa.objects.select_related('solicitante', 'fornecedor', 'filial').prefetch_related('logs')
    if filtro_tipo:
        qs = qs.filter(tipo_lancamento=filtro_tipo)
    if filtro_status:
        qs = qs.filter(status=filtro_status)
    if filtro_de:
        qs = qs.filter(data_criacao__date__gte=filtro_de)
    if filtro_ate:
        qs = qs.filter(data_criacao__date__lte=filtro_ate)

    resultados = []
    contadores = {'NO_PRAZO': 0, 'A_VENCER': 0, 'EM_ATRASO': 0, 'FECHADO_ATRASO': 0, 'FECHADO_OK': 0}

    for despesa in qs:
        status_atual = despesa.status
        is_final = status_atual in STATUS_FINAIS

        if is_final:
            # Tempo total de vida: criação → última alteração
            if despesa.data_criacao and despesa.data_ultima_alteracao:
                tempo_total_h = (despesa.data_ultima_alteracao - despesa.data_criacao).total_seconds() / 3600
            else:
                tempo_total_h = 0
            soma_sla = sum(sla_map.values()) if sla_map else None
            if soma_sla:
                situacao = 'FECHADO_OK' if tempo_total_h <= soma_sla else 'FECHADO_ATRASO'
            else:
                situacao = 'FECHADO_OK'
            tempo_display = tempo_total_h
            prazo_ref = soma_sla
            excesso_h = max(0, tempo_total_h - soma_sla) if soma_sla else 0
        else:
            # Tempo no status atual: última alteração → agora
            prazo_h = sla_map.get(status_atual)
            if despesa.data_ultima_alteracao:
                tempo_no_status_h = (agora - despesa.data_ultima_alteracao).total_seconds() / 3600
            else:
                tempo_no_status_h = 0

            tempo_display = tempo_no_status_h
            prazo_ref = prazo_h
            excesso_h = 0

            if prazo_h is None:
                situacao = 'NO_PRAZO'
            elif tempo_no_status_h >= prazo_h:
                situacao = 'EM_ATRASO'
                excesso_h = tempo_no_status_h - prazo_h
            elif tempo_no_status_h >= prazo_h * 0.8:
                situacao = 'A_VENCER'
            else:
                situacao = 'NO_PRAZO'

        contadores[situacao] += 1

        if filtro_sla and situacao != filtro_sla:
            continue

        def fmt_horas(h):
            if h is None:
                return '—'
            h = int(h)
            d, hr = divmod(h, 24)
            partes = []
            if d: partes.append(f"{d}d")
            if hr: partes.append(f"{hr}h")
            return " ".join(partes) or "< 1h"

        resultados.append({
            'despesa': despesa,
            'situacao': situacao,
            'tempo_h': tempo_display,
            'tempo_fmt': fmt_horas(tempo_display),
            'prazo_h': prazo_ref,
            'prazo_fmt': fmt_horas(prazo_ref),
            'excesso_fmt': fmt_horas(excesso_h) if excesso_h else '',
            'status_label': STATUS_LABELS.get(status_atual, status_atual),
            'is_final': is_final,
        })

    # Ordena: em atraso primeiro, depois a vencer, etc.
    ordem = {'EM_ATRASO': 0, 'FECHADO_ATRASO': 1, 'A_VENCER': 2, 'FECHADO_OK': 3, 'NO_PRAZO': 4}
    resultados.sort(key=lambda r: (ordem.get(r['situacao'], 9), -(r['tempo_h'] or 0)))

    total = sum(contadores.values())
    pct = lambda v: round(v / total * 100) if total else 0

    from django.contrib import admin as dj_admin
    context = {
        **dj_admin.site.each_context(request),
        'title': 'Painel de SLA — Workflow',
        'resultados': resultados,
        'contadores': contadores,
        'total': total,
        'pct_no_prazo':       pct(contadores['NO_PRAZO']),
        'pct_a_vencer':       pct(contadores['A_VENCER']),
        'pct_em_atraso':      pct(contadores['EM_ATRASO']),
        'pct_fechado_atraso': pct(contadores['FECHADO_ATRASO']),
        'pct_fechado_ok':     pct(contadores['FECHADO_OK']),
        'filtro_tipo':   filtro_tipo,
        'filtro_status': filtro_status,
        'filtro_sla':    filtro_sla,
        'filtro_de':     filtro_de,
        'filtro_ate':    filtro_ate,
        'tipo_choices':   [('CAIXINHA','Caixinha'),('SOLICITACAO','Solicitação'),('EXTRA','Extra')],
        'status_choices': [(s, l) for s, l in STATUS_WORKFLOW if s not in STATUS_FINAIS],
        'sla_map': sla_map,
        'sem_sla': not sla_map,
    }
    return render(request, 'admin/workflow/painel_sla.html', context)
