from datetime import datetime
from collections import Counter
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F
from django.http import JsonResponse, HttpResponse
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
            filial_nome=F('colaborador_faltou__filial__nome'),
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
        'querystring': request.GET.urlencode(),
    }
    return render(request, 'admin/workflow/relatorio_coberturas.html', context)


@staff_member_required
def exportar_coberturas_detalhado(request):
    """
    Exporta um CSV com uma linha por DIA de falta (não por WF), usando os
    mesmos filtros da tela de Relatório de Coberturas — para rastrear as
    faltas dia a dia em outro sistema.
    """
    import csv
    from workflow.models import Despesa

    DIAS_SEMANA = {
        1: 'Domingo', 2: 'Segunda-feira', 3: 'Terça-feira', 4: 'Quarta-feira',
        5: 'Quinta-feira', 6: 'Sexta-feira', 7: 'Sábado',
    }

    qs = Despesa.objects.filter(
        status='PAGO',
        fornecedor__plano_de_contas__nome='Cobertura Falta',
    ).select_related('colaborador_faltou', 'colaborador_faltou__filial', 'motivo_ausencia')

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

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="coberturas_faltas_detalhado.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Data da Falta', 'Dia da Semana', 'Colaborador', 'Filial',
        'Motivo', 'WF #', 'Valor da Ocorrência (WF)',
    ])

    for d in qs.order_by('data_despesa'):
        datas = []
        dias_cob = (d.dias_cobertura or '').strip()
        if dias_cob:
            for parte in dias_cob.split(','):
                parte = parte.strip()
                if not parte:
                    continue
                try:
                    datas.append(datetime.strptime(parte, '%d-%m-%Y').date())
                except ValueError:
                    continue
        elif d.data_despesa:
            datas = [d.data_despesa]

        colaborador = d.colaborador_faltou.nome if d.colaborador_faltou else ''
        filial = d.colaborador_faltou.filial if (d.colaborador_faltou and d.colaborador_faltou.filial_id) else ''
        motivo = d.motivo_ausencia.nome if d.motivo_ausencia else ''

        for dt in sorted(datas):
            nome_dia = DIAS_SEMANA[dt.isoweekday() % 7 + 1]
            writer.writerow([
                dt.strftime('%d/%m/%Y'), nome_dia, colaborador, filial,
                motivo, d.id, f'{d.valor:.2f}'.replace('.', ','),
            ])

    return response


@staff_member_required
def painel_sla(request):
    import datetime, calendar
    from .models import Despesa, ConfiguracaoSLA, STATUS_WORKFLOW
    from django.contrib import admin as dj_admin
    from django.db.models import Count, F

    STATUS_FINAIS     = {'PAGO', 'CONFERIDO', 'CANCELADO'}
    STATUS_FINAIS_OK  = {'PAGO', 'CONFERIDO'}
    STATUS_ABERTOS    = {'AGUARDANDO_COMERCIAL','AGUARDANDO_ADM','AGUARDANDO_RH','AGUARDANDO_FIN','DIRECIONADO_OP'}
    STATUS_APROVADOR  = {
        'AGUARDANDO_COMERCIAL': 'Comercial',
        'AGUARDANDO_ADM':       'Administrativo',
        'AGUARDANDO_RH':        'RH',
        'AGUARDANDO_FIN':       'Financeiro',
        'DIRECIONADO_OP':       'Operador',
    }

    agora = tz.now()
    hoje  = agora.date()

    # ── Período selecionado (default = mês atual até hoje) ──────────────
    filtro_tipo = request.GET.get('tipo', '')
    filtro_de   = request.GET.get('data_de', '')
    filtro_ate  = request.GET.get('data_ate', '')

    data_inicio = datetime.date.fromisoformat(filtro_de)  if filtro_de  else hoje.replace(day=1)
    data_fim    = datetime.date.fromisoformat(filtro_ate) if filtro_ate else hoje

    # Mesmo período do mês anterior
    m_ant  = data_inicio.month - 1 or 12
    a_ant  = data_inicio.year - (1 if data_inicio.month == 1 else 0)
    max_d  = calendar.monthrange(a_ant, m_ant)[1]
    data_inicio_ant = data_inicio.replace(year=a_ant, month=m_ant)
    data_fim_ant    = data_fim.replace(   year=a_ant, month=m_ant, day=min(data_fim.day, max_d))

    # ── SLA config ───────────────────────────────────────────────────────
    sla_map    = {s.status: s.total_horas for s in ConfiguracaoSLA.objects.filter(ativo=True)}
    soma_sla_h = sum(sla_map.values()) if sla_map else None

    # ── Helpers ──────────────────────────────────────────────────────────
    def horas_vida(d):
        fim = d.data_ultima_alteracao if d.status in STATUS_FINAIS_OK else agora
        if not d.data_criacao:
            return 0
        return (fim - d.data_criacao).total_seconds() / 3600

    def dentro_sla(d):
        if soma_sla_h is None:
            return True
        return horas_vida(d) <= soma_sla_h

    def pct_delta(atual, ant):
        if ant == 0:
            return None
        return round((atual - ant) / ant * 100, 1)

    # ── Base QS ──────────────────────────────────────────────────────────
    qs_all = Despesa.objects.select_related('solicitante', 'motivo_ausencia')
    if filtro_tipo:
        qs_all = qs_all.filter(tipo_lancamento=filtro_tipo)

    def metrics(qs):
        lst = list(qs)
        total      = len(lst)
        abertos    = sum(1 for d in lst if d.status in STATUS_ABERTOS)
        atendidos  = sum(1 for d in lst if d.status in STATUS_FINAIS_OK and dentro_sla(d))
        extrapol   = sum(1 for d in lst if not dentro_sla(d))
        return total, abertos, atendidos, extrapol

    qs_per = qs_all.filter(data_criacao__date__gte=data_inicio,     data_criacao__date__lte=data_fim)
    qs_ant = qs_all.filter(data_criacao__date__gte=data_inicio_ant, data_criacao__date__lte=data_fim_ant)

    tot,  ab,  atd,  ext  = metrics(qs_per)
    tot_a, ab_a, atd_a, ext_a = metrics(qs_ant)

    cards = {
        'aberto':      {'v': ab,  'ant': ab_a,  'delta': pct_delta(ab,  ab_a),  'icon':'fas fa-clock',        'cor':'#e67e22'},
        'total':       {'v': tot, 'ant': tot_a, 'delta': pct_delta(tot, tot_a), 'icon':'fas fa-layer-group',  'cor':'#8e44ad'},
        'atendido':    {'v': atd, 'ant': atd_a, 'delta': pct_delta(atd, atd_a), 'icon':'fas fa-check-circle', 'cor':'#27ae60'},
        'extrapolado': {'v': ext, 'ant': ext_a, 'delta': pct_delta(ext, ext_a), 'icon':'fas fa-hourglass-end','cor':'#e74c3c'},
    }

    pct_sla_gauge = round(atd / tot * 100) if tot else 0

    # ── Gráfico 1: Em aberto por motivo ──────────────────────────────────
    qs_aberto = qs_per.filter(status__in=STATUS_ABERTOS)
    _motivo_count = {}
    for d in qs_aberto.select_related('motivo_ausencia'):
        nome = (d.motivo_ausencia.nome if d.motivo_ausencia_id
                else d.get_tipo_lancamento_display().upper())
        _motivo_count[nome] = _motivo_count.get(nome, 0) + 1
    aberto_por_motivo = [
        {'nome': k, 'qtd': v}
        for k, v in sorted(_motivo_count.items(), key=lambda x: -x[1])
    ][:12]

    # ── Gráfico 2: Em aberto por aprovador (status) ──────────────────────
    aprov_raw = (
        qs_aberto
        .values('status')
        .annotate(qtd=Count('id'))
        .order_by('-qtd')
    )
    aberto_por_aprovador = [
        {'nome': STATUS_APROVADOR.get(r['status'], r['status']), 'qtd': r['qtd']}
        for r in aprov_raw
    ]

    # ── Gráfico 3: SLA atendido por solicitante ───────────────────────────
    atd_user = {}
    for d in qs_per:
        if d.status in STATUS_FINAIS_OK and dentro_sla(d):
            nome = d.solicitante.get_full_name() or d.solicitante.username
            atd_user[nome] = atd_user.get(nome, 0) + 1
    atd_por_usuario = sorted(atd_user.items(), key=lambda x: -x[1])[:10]
    atd_por_usuario = [{'nome': k, 'qtd': v} for k, v in atd_por_usuario]

    # ── Gráfico 4: SLA extrapolado por motivo ────────────────────────────
    ext_motivo = {}
    for d in qs_per:
        if not dentro_sla(d):
            nome = (d.motivo_ausencia.nome if d.motivo_ausencia_id
                    else d.get_tipo_lancamento_display())
            ext_motivo[nome] = ext_motivo.get(nome, 0) + 1
    ext_por_motivo = sorted(ext_motivo.items(), key=lambda x: -x[1])[:12]
    ext_por_motivo = [{'nome': k, 'qtd': v} for k, v in ext_por_motivo]

    # max para escala das barras
    def _max(lst): return max((r['qtd'] for r in lst), default=1)

    context = {
        **dj_admin.site.each_context(request),
        'title': 'SLA de Atendimento',
        'cards': cards,
        'pct_sla_gauge':      pct_sla_gauge,
        'aberto_por_motivo':  aberto_por_motivo,
        'max_motivo':         _max(aberto_por_motivo),
        'aberto_por_aprov':   aberto_por_aprovador,
        'max_aprov':          _max(aberto_por_aprovador),
        'atd_por_usuario':    atd_por_usuario,
        'max_usuario':        _max(atd_por_usuario),
        'ext_por_motivo':     ext_por_motivo,
        'max_ext':            _max(ext_por_motivo),
        'data_inicio':        data_inicio,
        'data_fim':           data_fim,
        'data_inicio_ant':    data_inicio_ant,
        'data_fim_ant':       data_fim_ant,
        'filtro_tipo':        filtro_tipo,
        'filtro_de':          filtro_de,
        'filtro_ate':         filtro_ate,
        'tipo_choices':       [('CAIXINHA','Caixinha'),('SOLICITACAO','Solicitação'),('EXTRA','Extra')],
        'sem_sla':            not sla_map,
    }
    return render(request, 'admin/workflow/painel_sla.html', context)


# ── versão tabela detalhada (mantida para acesso direto) ─────────────────────
@staff_member_required
def painel_sla_tabela(request):
    from .models import Despesa, ConfiguracaoSLA, LogWorkflow, STATUS_WORKFLOW
    from django.contrib import admin as dj_admin

    # Carrega configurações de SLA ativas
    sla_map = {
        s.status: s.total_horas
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

    # Mapa de ações → status que o WF ENTRA após aquela ação
    ACAO_PARA_STATUS = {
        'Aprovou → RH':              'AGUARDANDO_RH',
        'Aprovou → Financeiro':      'AGUARDANDO_FIN',
        'Direcionou ao Operador':    'DIRECIONADO_OP',
        'Retornou ao Administrativo':'AGUARDANDO_ADM',
        'Devolveu ao Financeiro':    'AGUARDANDO_FIN',
        'FINALIZOU (PAGO)':          'PAGO',
        'CONFERIDO':                 'CONFERIDO',
        'CANCELOU':                  'CANCELADO',
    }

    # Status em que o WF estava ANTES de cada ação de transição
    ACAO_STATUS_ANTERIOR = {
        'Aprovou → RH':              'AGUARDANDO_ADM',
        'Aprovou → Financeiro':      'AGUARDANDO_RH',
        'Direcionou ao Operador':    'AGUARDANDO_FIN',
        'Retornou ao Administrativo':'AGUARDANDO_RH',
        'Devolveu ao Financeiro':    'DIRECIONADO_OP',
        'FINALIZOU (PAGO)':          'DIRECIONADO_OP',
        'CONFERIDO':                 'AGUARDANDO_FIN',
        'CANCELOU':                  None,
    }

    # Status inicial padrão por tipo (quando não há como inferir)
    TIPO_STATUS_INICIAL = {
        'CAIXINHA':   'AGUARDANDO_FIN',
        'SOLICITACAO':'AGUARDANDO_RH',
        'EXTRA':      'AGUARDANDO_FIN',
    }

    # Etapas que nos interessam exibir, em ordem de fluxo
    ETAPAS_EXIBIR = [
        ('AGUARDANDO_ADM', 'ADM', '#3498db'),
        ('AGUARDANDO_RH',  'RH',  '#27ae60'),
        ('AGUARDANDO_FIN', 'FIN', '#f39c12'),
        ('DIRECIONADO_OP', 'OP',  '#8e44ad'),
        ('AGUARDANDO_COMERCIAL', 'COM', '#16a085'),
    ]

    def _fmt_horas_curto(h):
        total_min = int(round(h * 60))
        dias, resto = divmod(total_min, 1440)
        horas, minutos = divmod(resto, 60)
        if dias:
            return f"{dias}d{horas}h" if horas else f"{dias}d"
        elif horas:
            return f"{horas}h{minutos:02d}m" if minutos else f"{horas}h"
        return f"{minutos}m"

    # De qual status o WF vinha antes de cada ação (usando perfil do executor como hint)
    PERFIL_STATUS_ORIGEM = {
        'RH':          'AGUARDANDO_RH',
        'Financeiro':  'AGUARDANDO_FIN',
        'Operador':    'DIRECIONADO_OP',
        'Administrativo': None,  # ambíguo — usa tipo
        'Admin':       None,
        'Solicitante': None,
    }

    def _inferir_status_anterior(log, tipo_lancamento):
        """Infere o status em que o WF estava ANTES de 'Retornou ao Administrativo'."""
        st = PERFIL_STATUS_ORIGEM.get(log.perfil_usuario)
        if st:
            return st
        return TIPO_STATUS_INICIAL.get(tipo_lancamento, 'AGUARDANDO_FIN')

    def calcular_tempo_por_etapa(despesa, logs_ordenados, agora):
        """Retorna dict {status: horas} com tempo acumulado em cada etapa."""
        tempos = {}

        # Determinar status inicial a partir da primeira ação de transição
        primeiro_log_transicao = next(
            (log for log in logs_ordenados if log.acao in ACAO_PARA_STATUS), None
        )
        if primeiro_log_transicao:
            acao = primeiro_log_transicao.acao
            if acao == 'Retornou ao Administrativo':
                # Usa perfil do executor para saber de onde voltou
                status_atual = _inferir_status_anterior(primeiro_log_transicao, despesa.tipo_lancamento)
            elif ACAO_STATUS_ANTERIOR.get(acao):
                status_atual = ACAO_STATUS_ANTERIOR[acao]
            else:
                status_atual = TIPO_STATUS_INICIAL.get(despesa.tipo_lancamento, 'AGUARDANDO_RH')
        else:
            # Sem transições: WF permanece no status atual desde a criação
            status_atual = despesa.status if despesa.status not in STATUS_FINAIS \
                           else TIPO_STATUS_INICIAL.get(despesa.tipo_lancamento, 'AGUARDANDO_RH')

        # Fallback de entrada: data_criacao do registro quando não há "Criou Registro" no log
        entrada = despesa.data_criacao

        for log in logs_ordenados:
            if log.acao == 'Criou Registro':
                entrada = log.data_hora
                continue
            novo_status = ACAO_PARA_STATUS.get(log.acao)
            if novo_status:
                if entrada and log.data_hora > entrada:
                    horas = (log.data_hora - entrada).total_seconds() / 3600
                    tempos[status_atual] = tempos.get(status_atual, 0) + horas
                status_atual = novo_status
                entrada = log.data_hora

        # Período atual ainda em aberto
        if entrada and status_atual not in STATUS_FINAIS:
            horas = (agora - entrada).total_seconds() / 3600
            tempos[status_atual] = tempos.get(status_atual, 0) + horas

        return tempos

    def fmt_etapas(tempos):
        """Retorna lista de dicts para renderizar a barra de timeline por etapa."""
        total_h = sum(tempos.values()) or 1
        partes = []
        for st, label, cor in ETAPAS_EXIBIR:
            h = tempos.get(st, 0)
            if h < 0.01:
                continue
            pct = round(h / total_h * 100, 1)
            partes.append({
                'label': label,
                'txt': _fmt_horas_curto(h),
                'cor': cor,
                'pct': pct,
            })
        return partes

    resultados = []
    contadores = {'NO_PRAZO': 0, 'A_VENCER': 0, 'EM_ATRASO': 0, 'FECHADO_ATRASO': 0, 'FECHADO_OK': 0}

    for despesa in qs:
        logs_ord = sorted(despesa.logs.all(), key=lambda l: l.data_hora)
        tempo_etapas = calcular_tempo_por_etapa(despesa, logs_ord, agora)
        etapas_fmt = fmt_etapas(tempo_etapas)

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
            'etapas_fmt': etapas_fmt,
        })

    # Ordena: em atraso primeiro, depois a vencer, etc.
    ordem = {'EM_ATRASO': 0, 'FECHADO_ATRASO': 1, 'A_VENCER': 2, 'FECHADO_OK': 3, 'NO_PRAZO': 4}
    resultados.sort(key=lambda r: (ordem.get(r['situacao'], 9), -(r['tempo_h'] or 0)))

    total = sum(contadores.values())
    pct = lambda v: round(v / total * 100) if total else 0

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
    return render(request, 'admin/workflow/painel_sla_tabela.html', context)


@staff_member_required
def api_colaborador_info(request):
    from cadastros.models import ColaboradorInfo
    pk = request.GET.get('id')
    if not pk:
        return JsonResponse({'error': 'id required'}, status=400)
    try:
        c = ColaboradorInfo.objects.get(pk=pk)
        linhas = []
        if c.chave_pix:
            tipo = c.get_tipo_pix_display() if c.tipo_pix else 'Pix'
            linhas.append(f"{tipo}: {c.chave_pix}")
        if c.cpf and c.tipo_pix != 'CPF':
            linhas.append(f"CPF: {c.cpf}")
        dados = '\n'.join(linhas)
        return JsonResponse({'nome': c.nome.upper(), 'dados': dados})
    except ColaboradorInfo.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
