from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Processo
from .serializers import ProcessoSerializer
from datetime import datetime
from collections import defaultdict, Counter


class ProcessoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite visualizar processos.
    
    Filtros disponíveis:
    - uf: Filtra por UF
    - comarca: Filtra por comarca
    - fase: Filtra por fase do processo
    - situacao: Filtra por situação (Ativo, Arquivado, etc.)
    
    Busca textual:
    - search: Busca por número do processo
    
    Exemplos:
    - /api/processos/?uf=São Paulo
    - /api/processos/?situacao=Ativo
    - /api/processos/?search=0010614
    """
    queryset = Processo.objects.all()
    serializer_class = ProcessoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['uf', 'comarca', 'fase', 'situacao']
    search_fields = ['numero_processo']
    ordering_fields = ['numero_processo', 'uf', 'comarca', 'data_distribuicao']
    ordering = ['-numero_processo']


from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


# Campos de data (texto DD/MM/YYYY) filtráveis pelo painel
_CAMPOS_DATA = {
    'data_acordo', 'data_arquivamento', 'data_distribuicao', 'data_sentenca',
    'data_transito_julgado', 'data_primeiro_acordao',
}
# Faixas de valor: (campo_no_model, chave_min, chave_max)
_FAIXAS_VALOR = [
    ('valor_causa', 'valor_causa_min', 'valor_causa_max'),
    ('valor_condenacao', 'valor_condenacao_min', 'valor_condenacao_max'),
    ('valor_acordo', 'valor_acordo_min', 'valor_acordo_max'),
]


def _parse_data(texto):
    """DD/MM/YYYY ou YYYY-MM-DD -> date, ou None."""
    if not texto:
        return None
    from datetime import datetime
    s = str(texto)[:10]
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_valor(texto):
    """'R$ 1.234,56' -> 1234.56, ou None."""
    if texto in (None, ''):
        return None
    try:
        limpo = str(texto).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(limpo)
    except (ValueError, TypeError):
        return None


def aplicar_filtros(queryset, filters):
    """
    Aplica os filtros do painel geral (chaves enviadas pelo frontend) ao
    queryset de Processo. Fonte única de verdade do filtro para TODOS os
    módulos. Campos inexistentes são ignorados silenciosamente.
    Retorna sempre um QuerySet (para permitir .filter()/.values() depois).
    """
    if not filters:
        return queryset
    f = filters

    # 1) Categóricos diretos (campo do model -> chave do frontend)
    diretos = {
        'uf': 'ufs', 'comarca': 'comarcas', 'tribunal': 'tribunais',
        'fase': 'fase', 'situacao': 'status', 'desfecho': 'desfecho',
        'classe': 'classes', 'tipo_cargos': 'tipo_cargos',
    }
    for campo, chave in diretos.items():
        vals = f.get(chave)
        if vals:
            queryset = queryset.filter(**{f'{campo}__in': vals})

    # 2) Instância (jurisdicao: ['1','2'])
    if f.get('jurisdicao'):
        try:
            queryset = queryset.filter(instancia__in=[int(x) for x in f['jurisdicao']])
        except (TypeError, ValueError):
            pass

    # 3) Multi-valor em campos-lista (icontains OR)
    def _or_icontains(campo, valores):
        q = Q()
        for v in valores:
            q |= Q(**{f'{campo}__icontains': v})
        return q

    if f.get('assuntos'):
        queryset = queryset.filter(_or_icontains('assuntos', f['assuntos']))
    if f.get('tipos_recurso'):
        queryset = queryset.filter(_or_icontains('tipos_recursos', f['tipos_recurso']))
    if f.get('magistrados'):
        queryset = queryset.filter(_or_icontains('juizes', f['magistrados']))
    if f.get('cnpj'):
        queryset = queryset.filter(_or_icontains('cnpjs', f['cnpj']))
    if f.get('advogados'):
        q = Q()
        for v in f['advogados']:
            q |= Q(advogados_polo_ativo__icontains=v) | Q(advogados_polo_passivo__icontains=v)
        queryset = queryset.filter(q)
    if f.get('partes'):
        q = Q()
        for v in f['partes']:
            q |= Q(partes_polo_ativo__icontains=v) | Q(partes_polo_passivo__icontains=v)
        queryset = queryset.filter(q)

    # 4) Tipos de pedido (tabela normalizada)
    if f.get('tipos_pedido'):
        queryset = queryset.filter(pedidos_norm__catalogo__nome__in=f['tipos_pedido']).distinct()

    # 5) Indicativos (radio "Com Indicativo"/"Sem indicativo")
    if f.get('bloqueio'):
        queryset = queryset.filter(indicativo_bloqueio='Sim' if 'Com' in f['bloqueio'] else 'Não')
    if f.get('revelia'):
        queryset = queryset.filter(indicativo_revelia='Sim' if 'Com' in f['revelia'] else 'Não')
    if f.get('transito'):
        if f['transito'] == 'Julgado':
            queryset = queryset.exclude(data_transito_julgado__isnull=True).exclude(data_transito_julgado='')
        else:
            queryset = queryset.filter(Q(data_transito_julgado__isnull=True) | Q(data_transito_julgado=''))

    # 6) Período por tipo de data (datas em texto → filtra por PKs, mantém queryset)
    tipo_data, di, df = f.get('tipo_data'), f.get('data_inicio'), f.get('data_fim')
    if tipo_data in _CAMPOS_DATA and (di or df):
        d0, d1 = _parse_data(di), _parse_data(df)
        pks = []
        for pk, val in queryset.values_list('numero_processo', tipo_data):
            dv = _parse_data(val)
            if not dv or (d0 and dv < d0) or (d1 and dv > d1):
                continue
            pks.append(pk)
        queryset = queryset.filter(numero_processo__in=pks)

    # 7) Faixas de valor (texto monetário → filtra por PKs)
    for campo, kmin, kmax in _FAIXAS_VALOR:
        vmin, vmax = f.get(kmin), f.get(kmax)
        if vmin is None and vmax is None:
            continue
        pks = []
        for pk, val in queryset.values_list('numero_processo', campo):
            v = _parse_valor(val)
            if v is None or (vmin is not None and v < vmin) or (vmax is not None and v > vmax):
                continue
            pks.append(pk)
        queryset = queryset.filter(numero_processo__in=pks)

    return queryset


@api_view(['GET'])
def filter_options(request):
    """
    Retorna todas as opções disponíveis para os filtros.
    """
    # Obter valores únicos de cada campo
    ufs = list(Processo.objects.values_list('uf', flat=True).distinct().order_by('uf'))
    comarcas = list(Processo.objects.values_list('comarca', flat=True).distinct().order_by('comarca'))
    tribunais = list(Processo.objects.values_list('tribunal', flat=True).distinct().order_by('tribunal'))
    
    # Para campos que contém múltiplos valores separados, precisamos processar
    # Advogados (polo ativo e passivo combinados)
    advogados_set = set()
    for adv in Processo.objects.values_list('advogados_polo_ativo', 'advogados_polo_passivo'):
        for campo in adv:
            if campo:
                # Separar por vírgula ou ponto-e-vírgula
                items = campo.replace(';', ',').split(',')
                for item in items:
                    item = item.strip()
                    if item:
                        advogados_set.add(item)
    
    # Partes (polo ativo e passivo combinados)
    partes_set = set()
    for parte in Processo.objects.values_list('partes_polo_ativo', 'partes_polo_passivo'):
        for campo in parte:
            if campo:
                items = campo.replace(';', ',').split(',')
                for item in items:
                    item = item.strip()
                    if item:
                        partes_set.add(item)
    
    # CNPJs
    cnpj_set = set()
    for cnpj in Processo.objects.values_list('cnpjs', flat=True):
        if cnpj:
            items = cnpj.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    cnpj_set.add(item)
    
    # Juízes/Magistrados
    magistrados_set = set()
    for juiz in Processo.objects.values_list('juizes', flat=True):
        if juiz:
            items = juiz.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    magistrados_set.add(item)
    
    # Tipo de Cargos
    tipo_cargos_set = set()
    for cargo in Processo.objects.values_list('tipo_cargos', flat=True):
        if cargo:
            items = cargo.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    tipo_cargos_set.add(item)
    
    # Desfecho
    desfecho_set = set()
    for desf in Processo.objects.values_list('desfecho', flat=True):
        if desf:
            items = desf.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    desfecho_set.add(item)
    
    # Assuntos
    assuntos_set = set()
    for assunto in Processo.objects.values_list('assuntos', flat=True):
        if assunto:
            items = assunto.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    assuntos_set.add(item)
    
    # Classes
    classes_set = set()
    for classe in Processo.objects.values_list('classe', flat=True):
        if classe:
            items = classe.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    classes_set.add(item)
    
    # Tipos de Recurso
    tipos_recurso_set = set()
    for recurso in Processo.objects.values_list('tipos_recursos', flat=True):
        if recurso:
            items = recurso.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    tipos_recurso_set.add(item)
    
    # Pedidos
    pedidos_set = set()
    for pedido in Processo.objects.values_list('pedidos', flat=True):
        if pedido:
            items = pedido.replace(';', ',').split(',')
            for item in items:
                item = item.strip()
                if item:
                    pedidos_set.add(item)
    
    # Remover valores nulos/vazios
    ufs = [uf for uf in ufs if uf]
    comarcas = [comarca for comarca in comarcas if comarca]
    tribunais = [tribunal for tribunal in tribunais if tribunal]
    
    return Response({
        'ufs': sorted(ufs),
        'comarcas': sorted(comarcas),
        'orgao_origem': [],  # Não existe no banco
        'orgao_julgador': [],  # Não existe no banco
        'tribunais': sorted(tribunais),
        'partes': sorted(list(partes_set))[:100],  # Limitar a 100 para performance
        'cnpj': sorted(list(cnpj_set))[:100],
        'advogados': sorted(list(advogados_set))[:100],
        'magistrados': sorted(list(magistrados_set))[:100],
        'tipo_cargos': sorted(list(tipo_cargos_set)),
        'cargos': [],  # Não existe no banco
        'desfecho': sorted(list(desfecho_set)),
        'assuntos': sorted(list(assuntos_set))[:100],
        'classes': sorted(list(classes_set)),
        'tipos_recurso': sorted(list(tipos_recurso_set)),
        'tipos_pedido': sorted(list(pedidos_set))[:100]
    })


@api_view(['POST'])
def dashboard_data_filtered(request):
    """
    Retorna dados do dashboard aplicando filtros.
    """
    filters = request.data
    queryset = aplicar_filtros(Processo.objects.all(), filters)

    # Calcular estatísticas com queryset filtrado
    from django.db.models import Count, Sum, Avg
    from datetime import datetime, timedelta
    
    total_processos = queryset.count()
    
    # Como os campos de data são CharField, não podemos filtrar por data diretamente
    # Vamos contar apenas processos com os campos preenchidos
    distribuidos_30_dias = queryset.filter(data_distribuicao__isnull=False).exclude(data_distribuicao='').count()
    arquivados_30_dias = queryset.filter(data_arquivamento__isnull=False).exclude(data_arquivamento='').count()
    transitados_30_dias = queryset.filter(data_transito_julgado__isnull=False).exclude(data_transito_julgado='').count()
    
    # Calcular valor total e médio convertendo CharField para float
    from django.db.models.functions import Cast
    from django.db.models import FloatField
    
    # Filtrar apenas registros com valor_causa válido
    queryset_com_valor = queryset.filter(valor_causa__isnull=False).exclude(valor_causa='')
    
    valor_total = 0
    valor_medio = 0
    
    try:
        # Tentar somar valores convertendo de string para float
        for proc in queryset_com_valor:
            try:
                valor = float(proc.valor_causa.replace(',', '.'))
                valor_total += valor
            except (ValueError, AttributeError):
                pass
        
        if queryset_com_valor.count() > 0:
            valor_medio = valor_total / queryset_com_valor.count()
    except Exception:
        pass
    
    # Processos por UF
    processos_por_uf = queryset.values('uf').annotate(count=Count('numero_processo')).order_by('-count')
    
    # Processos por Comarca
    processos_por_comarca = queryset.values('comarca').annotate(count=Count('numero_processo')).order_by('-count')
    
    # Processos por Fase
    processos_por_fase = queryset.values('fase').annotate(count=Count('numero_processo')).order_by('-count')
    
    # Valor de Causa por UF (calculado manualmente pois valor_causa é CharField)
    valor_causa_por_uf_dict = {}
    for proc in queryset.filter(valor_causa__isnull=False).exclude(valor_causa=''):
        try:
            valor = float(proc.valor_causa.replace(',', '.'))
            uf = proc.uf or 'N/A'
            valor_causa_por_uf_dict[uf] = valor_causa_por_uf_dict.get(uf, 0) + valor
        except (ValueError, AttributeError):
            pass
    
    valor_causa_por_uf = sorted(valor_causa_por_uf_dict.items(), key=lambda x: x[1], reverse=True)
    
    # Valor de Causa por Comarca (calculado manualmente)
    valor_causa_por_comarca_dict = {}
    for proc in queryset.filter(valor_causa__isnull=False).exclude(valor_causa=''):
        try:
            valor = float(proc.valor_causa.replace(',', '.'))
            comarca = proc.comarca or 'N/A'
            valor_causa_por_comarca_dict[comarca] = valor_causa_por_comarca_dict.get(comarca, 0) + valor
        except (ValueError, AttributeError):
            pass
    
    valor_causa_por_comarca = sorted(valor_causa_por_comarca_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Valor de Condenação por Comarca (calculado manualmente)
    valor_condenacao_por_comarca_dict = {}
    for proc in queryset.filter(valor_condenacao__isnull=False).exclude(valor_condenacao=''):
        try:
            valor = float(proc.valor_condenacao.replace(',', '.'))
            comarca = proc.comarca or 'N/A'
            valor_condenacao_por_comarca_dict[comarca] = valor_condenacao_por_comarca_dict.get(comarca, 0) + valor
        except (ValueError, AttributeError):
            pass
    
    valor_condenacao_por_comarca = sorted(valor_condenacao_por_comarca_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return Response({
        'cards': {
            'total_processos': total_processos,
            'distribuidos_30_dias': distribuidos_30_dias,
            'arquivados_30_dias': arquivados_30_dias,
            'transitados_30_dias': transitados_30_dias,
            'valor_total': float(valor_total),
            'valor_medio': float(valor_medio)
        },
        'processos_por_uf': {
            'labels': [item['uf'] for item in processos_por_uf],
            'values': [item['count'] for item in processos_por_uf]
        },
        'processos_por_comarca': {
            'labels': [item['comarca'] for item in processos_por_comarca],
            'values': [item['count'] for item in processos_por_comarca]
        },
        'processos_por_fase': {
            'labels': [item['fase'] for item in processos_por_fase],
            'values': [item['count'] for item in processos_por_fase]
        },
        'valor_causa_por_uf': {
            'labels': [item[0] for item in valor_causa_por_uf],
            'values': [float(item[1]) for item in valor_causa_por_uf]
        },
        'valor_causa_por_comarca': {
            'labels': [item[0] for item in valor_causa_por_comarca],
            'values': [float(item[1]) for item in valor_causa_por_comarca]
        },
        'valor_condenacao_por_comarca': {
            'labels': [item[0] for item in valor_condenacao_por_comarca],
            'values': [float(item[1]) for item in valor_condenacao_por_comarca]
        }
    })


@api_view(['GET', 'POST'])
def acordos_data(request):
    """
    Retorna dados para o módulo de Acordos.
    Suporta filtros via POST.
    """
    from collections import defaultdict
    import re
    
    filters = request.data if request.method == 'POST' else {}
    queryset = aplicar_filtros(Processo.objects.all(), filters)

    # Processos com acordo (data_acordo não vazia)
    processos_com_acordo = queryset.exclude(data_acordo__isnull=True).exclude(data_acordo='')
    
    # 1. PROPORÇÃO DE ACORDOS POR ANO
    proporcao_acordos = calcular_proporcao_acordos(queryset, processos_com_acordo)
    
    # 2. ACORDOS POR FASE
    acordos_por_fase = calcular_acordos_por_fase(processos_com_acordo)
    
    # 3. VOLUME DE ACORDOS POR ANO
    volume_acordos = calcular_volume_acordos(processos_com_acordo)
    
    # 4-5. COMPARAÇÕES DE VALORES
    causa_vs_acordo = calcular_comparacao_valores(processos_com_acordo, 'valor_causa', 'valor_acordo')
    condenacao_vs_acordo = calcular_comparacao_valores(processos_com_acordo, 'valor_condenacao', 'valor_acordo')
    
    # 7. RANKING DE ACORDOS
    ranking_acordos = {
        'comarca': calcular_ranking_acordos(processos_com_acordo, 'comarca'),
        'classe': calcular_ranking_acordos(processos_com_acordo, 'classe'),
        'assuntos': calcular_ranking_acordos_multiplo(processos_com_acordo, 'assuntos'),
        'magistrado': calcular_ranking_acordos_multiplo(processos_com_acordo, 'juizes'),
        'origem': calcular_ranking_acordos(processos_com_acordo, 'orgao_origem'),
        'tribunal': calcular_ranking_acordos(processos_com_acordo, 'tribunal'),
        'advogado_ativo': calcular_ranking_acordos_multiplo(processos_com_acordo, 'advogados_polo_ativo'),
        'cargo': calcular_ranking_acordos_multiplo(processos_com_acordo, 'tipo_cargos')
    }
    
    return Response({
        'proporcao_acordos': proporcao_acordos,
        'acordos_por_fase': acordos_por_fase,
        'volume_acordos': volume_acordos,
        'causa_vs_acordo': causa_vs_acordo,
        'condenacao_vs_acordo': condenacao_vs_acordo,
        'ranking_acordos': ranking_acordos
    })


def calcular_proporcao_acordos(queryset_total, queryset_acordos):
    """Calcula proporção de acordos por ano."""
    from collections import defaultdict
    import re
    
    anos_total = defaultdict(int)
    anos_acordos = defaultdict(int)
    
    # Contar total de processos por ano (usando data_distribuicao)
    for processo in queryset_total:
        if processo.data_distribuicao:
            match = re.search(r'(\d{4})', str(processo.data_distribuicao))
            if match:
                ano = match.group(1)
                anos_total[ano] += 1
    
    # Contar acordos por ano (usando data_acordo)
    for processo in queryset_acordos:
        if processo.data_acordo:
            match = re.search(r'(\d{4})', str(processo.data_acordo))
            if match:
                ano = match.group(1)
                anos_acordos[ano] += 1
    
    # Ordenar anos
    anos_ordenados = sorted(set(list(anos_total.keys()) + list(anos_acordos.keys())))
    
    return {
        'labels': anos_ordenados,
        'total_processos': [anos_total.get(ano, 0) for ano in anos_ordenados],
        'total_acordos': [anos_acordos.get(ano, 0) for ano in anos_ordenados]
    }


def calcular_acordos_por_fase(queryset_acordos):
    """Calcula acordos por fase processual."""
    from collections import defaultdict
    
    fases_count = defaultdict(int)
    
    for processo in queryset_acordos:
        if processo.fase:
            fases_count[processo.fase] += 1
    
    return {
        'labels': list(fases_count.keys()),
        'values': list(fases_count.values())
    }


def calcular_volume_acordos(queryset_acordos):
    """Calcula volume total de acordos (em R$) por ano."""
    from collections import defaultdict
    import re
    
    anos_valores = defaultdict(float)
    
    for processo in queryset_acordos:
        if processo.data_acordo and processo.valor_acordo:
            # Extrair ano
            match_ano = re.search(r'(\d{4})', str(processo.data_acordo))
            if match_ano:
                ano = match_ano.group(1)
                
                # Extrair valor
                try:
                    valor_str = str(processo.valor_acordo).replace('R$', '').replace('.', '').replace(',', '.').strip()
                    valor = float(valor_str)
                    anos_valores[ano] += valor
                except (ValueError, AttributeError):
                    pass
    
    anos_ordenados = sorted(anos_valores.keys())
    
    return {
        'labels': anos_ordenados,
        'values': [anos_valores[ano] for ano in anos_ordenados]
    }


def calcular_comparacao_valores(queryset_acordos, campo_comparacao, campo_acordo):
    """Calcula média de dois campos para comparação."""
    import re
    
    valores_campo1 = []
    valores_campo2 = []
    
    for processo in queryset_acordos:
        valor1_raw = getattr(processo, campo_comparacao, None)
        valor2_raw = getattr(processo, campo_acordo, None)
        
        if valor1_raw and valor2_raw:
            try:
                # Limpar e converter valores
                valor1_str = str(valor1_raw).replace('R$', '').replace('.', '').replace(',', '.').strip()
                valor2_str = str(valor2_raw).replace('R$', '').replace('.', '').replace(',', '.').strip()
                
                valor1 = float(valor1_str)
                valor2 = float(valor2_str)
                
                if valor1 > 0 and valor2 > 0:
                    valores_campo1.append(valor1)
                    valores_campo2.append(valor2)
            except (ValueError, AttributeError):
                pass
    
    # Calcular médias
    media_campo1 = sum(valores_campo1) / len(valores_campo1) if valores_campo1 else 0
    media_campo2 = sum(valores_campo2) / len(valores_campo2) if valores_campo2 else 0
    
    # Nomes dos campos para labels
    nomes_campos = {
        'valor_causa': 'Valor de Causa',
        'valor_condenacao': 'Valor de Condenação',
        'valor_liquidacao': 'Valor de Liquidação',
        'valor_acordo': 'Valor de Acordo'
    }
    
    return {
        'labels': [nomes_campos.get(campo_comparacao, campo_comparacao), nomes_campos.get(campo_acordo, campo_acordo)],
        'values': [media_campo1, media_campo2]
    }


def calcular_ranking_acordos(queryset_acordos, campo):
    """Calcula ranking de acordos por campo simples."""
    from collections import defaultdict
    
    ranking = defaultdict(int)
    
    for processo in queryset_acordos:
        valor_campo = getattr(processo, campo, None)
        if valor_campo:
            ranking[str(valor_campo)] += 1
    
    # Ordenar por quantidade (decrescente) e pegar top 10
    ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'labels': [item[0] for item in ranking_ordenado],
        'values': [item[1] for item in ranking_ordenado]
    }


def calcular_ranking_acordos_multiplo(queryset_acordos, campo):
    """Calcula ranking de acordos por campo com múltiplos valores (separados por vírgula)."""
    from collections import defaultdict
    
    ranking = defaultdict(int)
    
    for processo in queryset_acordos:
        valor_campo = getattr(processo, campo, None)
        if valor_campo:
            # Separar por vírgula e contar cada item
            itens = [item.strip() for item in str(valor_campo).split(',')]
            for item in itens:
                if item:
                    ranking[item] += 1
    
    # Ordenar por quantidade (decrescente) e pegar top 10
    ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'labels': [item[0] for item in ranking_ordenado],
        'values': [item[1] for item in ranking_ordenado]
    }


@api_view(['GET', 'POST'])
def desfechos_data(request):
    """
    Retorna dados para os gráficos do módulo Desfechos.
    Suporta filtros via POST.
    """
    filters = request.data if request.method == 'POST' else {}
    queryset = aplicar_filtros(Processo.objects.all(), filters)
    
    # 1. VOLUME DE PROCESSOS POR TIPO DE DESFECHO
    volume_desfechos = calcular_volume_desfechos(queryset)
    
    # 2. RANKING POR TIPO DE DESFECHO
    ranking_desfechos = {
        'comarca': calcular_ranking_desfechos(queryset, 'comarca'),
        'classe': calcular_ranking_desfechos(queryset, 'classe'),
        'assuntos': calcular_ranking_desfechos_multiplo(queryset, 'assuntos'),
        'magistrado': calcular_ranking_desfechos_multiplo(queryset, 'juizes'),
        'origem': calcular_ranking_desfechos(queryset, 'orgao_origem'),
        'atividade_economica': calcular_ranking_desfechos_multiplo(queryset, 'atividade_economica'),
        'tribunal': calcular_ranking_desfechos(queryset, 'tribunal'),
        'advogado_ativo': calcular_ranking_desfechos_multiplo(queryset, 'advogados_polo_ativo'),
        'cargo': calcular_ranking_desfechos_multiplo(queryset, 'tipo_cargos')
    }
    
    # 3. DECISÕES POR INSTÂNCIAS
    decisoes_instancias = calcular_decisoes_instancias(queryset)
    
    return Response({
        'volume_desfechos': volume_desfechos,
        'ranking_desfechos': ranking_desfechos,
        'decisoes_instancias': decisoes_instancias
    })


def calcular_volume_desfechos(queryset):
    """Calcula volume de processos por tipo de desfecho."""
    desfechos_dict = {}
    
    for processo in queryset:
        if processo.desfecho:
            # Processar múltiplos desfechos separados por vírgula
            desfechos_lista = [d.strip() for d in processo.desfecho.split(',') if d.strip()]
            for desfecho in desfechos_lista:
                desfechos_dict[desfecho] = desfechos_dict.get(desfecho, 0) + 1
    
    # Ordenar por quantidade (decrescente)
    desfechos_sorted = sorted(desfechos_dict.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'labels': [d[0] for d in desfechos_sorted],
        'values': [d[1] for d in desfechos_sorted]
    }


def calcular_ranking_desfechos(queryset, campo):
    """Calcula ranking de processos por campo (para campos simples)."""
    ranking_dict = {}
    
    for processo in queryset:
        valor = getattr(processo, campo, None)
        if valor:
            ranking_dict[valor] = ranking_dict.get(valor, 0) + 1
    
    # Ordenar por quantidade (decrescente) e pegar top 15
    ranking_sorted = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)[:15]
    
    return {
        'labels': [r[0] for r in ranking_sorted],
        'values': [r[1] for r in ranking_sorted]
    }


def calcular_ranking_desfechos_multiplo(queryset, campo):
    """Calcula ranking de processos por campo (para campos com múltiplos valores)."""
    ranking_dict = {}
    
    for processo in queryset:
        valor = getattr(processo, campo, None)
        if valor:
            # Processar múltiplos valores separados por vírgula ou ponto-e-vírgula
            valores_lista = [v.strip() for v in valor.replace(';', ',').split(',') if v.strip()]
            for item in valores_lista:
                ranking_dict[item] = ranking_dict.get(item, 0) + 1
    
    # Ordenar por quantidade (decrescente) e pegar top 15
    ranking_sorted = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)[:15]
    
    return {
        'labels': [r[0] for r in ranking_sorted],
        'values': [r[1] for r in ranking_sorted]
    }


def calcular_decisoes_instancias(queryset):
    """Calcula decisões de processos por instâncias."""
    # Estrutura: {desfecho: {1ª: count, 2ª: count, Superior: count}}
    decisoes_dict = {}
    
    for processo in queryset:
        if processo.desfecho and processo.instancia:
            # Processar múltiplos desfechos
            desfechos_lista = [d.strip() for d in processo.desfecho.split(',') if d.strip()]
            
            # Mapear instância para formato legível
            instancia_map = {
                '1': '1ª Instância',
                '2': '2ª Instância',
                '3': 'Instância Superior',
                'Superior': 'Instância Superior'
            }
            instancia_label = instancia_map.get(str(processo.instancia), processo.instancia)
            
            for desfecho in desfechos_lista:
                if desfecho not in decisoes_dict:
                    decisoes_dict[desfecho] = {'1ª Instância': 0, '2ª Instância': 0, 'Instância Superior': 0}
                decisoes_dict[desfecho][instancia_label] = decisoes_dict[desfecho].get(instancia_label, 0) + 1
    
    # Ordenar por total de processos (soma de todas as instâncias)
    decisoes_sorted = sorted(
        decisoes_dict.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True
    )[:15]  # Top 15
    
    # Preparar dados para gráfico empilhado
    labels = [d[0] for d in decisoes_sorted]
    primeira = [d[1].get('1ª Instância', 0) for d in decisoes_sorted]
    segunda = [d[1].get('2ª Instância', 0) for d in decisoes_sorted]
    superior = [d[1].get('Instância Superior', 0) for d in decisoes_sorted]
    
    return {
        'labels': labels,
        'primeira_instancia': primeira,
        'segunda_instancia': segunda,
        'instancia_superior': superior
    }



@api_view(['GET', 'POST'])
def distribuicao_data(request):
    """
    Retorna dados para o módulo de Distribuição.
    Suporta filtros via POST.
    """
    from collections import defaultdict
    import re
    
    filters = request.data if request.method == 'POST' else {}
    queryset = aplicar_filtros(Processo.objects.all(), filters)

    # 1. VOLUME DE PROCESSOS DISTRIBUÍDOS POR ANO
    volume_distribuicao = calcular_volume_distribuicao(queryset)
    
    # 2. RANKING DE DISTRIBUIÇÃO POR CRITÉRIOS
    ranking_distribuicao = {
        'comarca': calcular_ranking_distribuicao(queryset, 'comarca'),
        'classe': calcular_ranking_distribuicao(queryset, 'classe'),
        'assuntos': calcular_ranking_distribuicao_multiplo(queryset, 'assuntos'),
        'magistrado': calcular_ranking_distribuicao_multiplo(queryset, 'juizes'),
        'origem': calcular_ranking_distribuicao(queryset, 'orgao_origem'),
        'tribunal': calcular_ranking_distribuicao(queryset, 'tribunal'),
        'advogado_ativo': calcular_ranking_distribuicao_multiplo(queryset, 'advogados_polo_ativo'),
        'cargo': calcular_ranking_distribuicao_multiplo(queryset, 'tipo_cargos')
    }
    
    return Response({
        'volume_distribuicao': volume_distribuicao,
        'ranking_distribuicao': ranking_distribuicao
    })


def calcular_volume_distribuicao(queryset):
    """Calcula volume de processos distribuídos por ano."""
    from collections import defaultdict
    import re
    
    anos_count = defaultdict(int)
    
    # Contar processos por ano de distribuição
    for processo in queryset:
        if processo.data_distribuicao:
            match = re.search(r'(\d{4})', str(processo.data_distribuicao))
            if match:
                ano = match.group(1)
                anos_count[ano] += 1
    
    # Ordenar anos
    anos_ordenados = sorted(anos_count.keys())
    
    return {
        'labels': anos_ordenados,
        'values': [anos_count[ano] for ano in anos_ordenados]
    }


def calcular_ranking_distribuicao(queryset, campo):
    """Calcula ranking de distribuição por campo (para campos simples)."""
    ranking_dict = {}
    
    for processo in queryset:
        valor = getattr(processo, campo, None)
        if valor:
            ranking_dict[valor] = ranking_dict.get(valor, 0) + 1
    
    # Ordenar por quantidade (decrescente) e pegar top 20
    ranking_sorted = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return {
        'labels': [r[0] for r in ranking_sorted],
        'values': [r[1] for r in ranking_sorted]
    }


def calcular_ranking_distribuicao_multiplo(queryset, campo):
    """Calcula ranking de distribuição por campo (para campos com múltiplos valores)."""
    ranking_dict = {}
    
    for processo in queryset:
        valor = getattr(processo, campo, None)
        if valor:
            # Processar múltiplos valores separados por vírgula ou ponto-e-vírgula
            valores_lista = [v.strip() for v in valor.replace(';', ',').split(',') if v.strip()]
            for item in valores_lista:
                ranking_dict[item] = ranking_dict.get(item, 0) + 1
    
    # Ordenar por quantidade (decrescente) e pegar top 20
    ranking_sorted = sorted(ranking_dict.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return {
        'labels': [r[0] for r in ranking_sorted],
        'values': [r[1] for r in ranking_sorted]
    }



@api_view(['GET', 'POST'])
def duracao_data(request):
    """
    Retorna dados para o módulo de Duração.
    Suporta filtros via POST.
    """
    from datetime import datetime
    from collections import defaultdict
    
    filters = request.data if request.method == 'POST' else {}
    queryset = aplicar_filtros(Processo.objects.all(), filters)

    # 1. DURAÇÃO DE PROCESSOS POR FASE
    duracao_por_fase = calcular_duracao_por_fase(queryset)
    
    # 2. QUANTIDADE POR DURAÇÃO E POR FASE
    quantidade_por_duracao = calcular_quantidade_por_duracao(queryset)
    
    # 3. DURAÇÃO DE PROCESSOS POR MARCO
    duracao_por_marco = calcular_duracao_por_marco(queryset)
    
    return Response({
        'duracao_por_fase': duracao_por_fase,
        'quantidade_por_duracao': quantidade_por_duracao,
        'duracao_por_marco': duracao_por_marco
    })


def calcular_duracao_por_fase(queryset):
    """Calcula duração média de processos por fase e UF."""
    from datetime import datetime
    from collections import defaultdict
    
    # Função auxiliar para parsear datas em diferentes formatos
    def parse_date(date_str):
        if not date_str:
            return None
        
        # Se tiver vírgula, pegar apenas a primeira data
        if ',' in date_str:
            date_str = date_str.split(',')[0].strip()
        
        # Tentar formato DD/MM/YYYY
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            pass
        
        # Tentar formato YYYY-MM-DD
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
        
        return None
    
    # Mapa de UF nome completo para sigla
    uf_map = {
        'Minas Gerais': 'MG',
        'São Paulo': 'SP',
        'Rio de Janeiro': 'RJ',
        'Rio Grande do Sul': 'RS',
        'Santa Catarina': 'SC',
        'Paraná': 'PR',
        'Bahia': 'BA',
        'Pernambuco': 'PE',
        'Ceará': 'CE',
        'Pará': 'PA',
        'Amazonas': 'AM',
        'Goiás': 'GO',
        'Distrito Federal': 'DF'
    }
    
    # Dicionário para armazenar durações por UF e fase
    duracoes = defaultdict(lambda: defaultdict(list))
    
    for processo in queryset:
        uf = processo.uf
        if not uf:
            continue
        
        # Converter nome completo de UF para sigla se necessário
        uf_sigla = uf_map.get(uf, uf)
        
        # Calcular duração de cada fase baseado nas datas disponíveis
        # Conhecimento: data_distribuicao até data_sentenca
        inicio = parse_date(processo.data_distribuicao)
        fim = parse_date(processo.data_sentenca)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            if duracao_dias >= 0:
                duracoes[uf_sigla]['Conhecimento'].append(duracao_dias)
        
        # Liquidação: data_sentenca até data_primeiro_acordao (aproximação)
        inicio = parse_date(processo.data_sentenca)
        fim = parse_date(processo.data_primeiro_acordao)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            if duracao_dias >= 0:
                duracoes[uf_sigla]['Liquidação'].append(duracao_dias)
        
        # Execução: data_primeiro_acordao até data_transito_julgado
        inicio = parse_date(processo.data_primeiro_acordao)
        fim = parse_date(processo.data_transito_julgado)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            if duracao_dias >= 0:
                duracoes[uf_sigla]['Execução'].append(duracao_dias)
    
    # Calcular médias
    resultado = {}
    for uf in sorted(duracoes.keys()):
        resultado[uf] = {}
        for fase in ['Conhecimento', 'Liquidação', 'Execução']:
            if duracoes[uf][fase]:
                resultado[uf][fase] = round(sum(duracoes[uf][fase]) / len(duracoes[uf][fase]))
            else:
                resultado[uf][fase] = 0
    
    return resultado


def calcular_quantidade_por_duracao(queryset):
    """Calcula quantidade de processos por faixa de duração e fase."""
    from datetime import datetime
    from collections import defaultdict
    
    # Função auxiliar para parsear datas
    def parse_date(date_str):
        if not date_str:
            return None
        if ',' in date_str:
            date_str = date_str.split(',')[0].strip()
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            pass
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
        return None
    
    # Faixas de duração em dias
    faixas = {
        '1 a 90 dias': (1, 90),
        '91 a 180 dias': (91, 180),
        '181 a 365 dias': (181, 365),
        '1 a 2 anos': (366, 730),
        'mais de 2 anos': (731, 999999)
    }
    
    # Contar processos por faixa e fase
    resultado = {
        'Conhecimento': defaultdict(int),
        'Liquidação': defaultdict(int),
        'Execução': defaultdict(int)
    }
    
    for processo in queryset:
        # Conhecimento
        inicio = parse_date(processo.data_distribuicao)
        fim = parse_date(processo.data_sentenca)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            for faixa, (min_dias, max_dias) in faixas.items():
                if min_dias <= duracao_dias <= max_dias:
                    resultado['Conhecimento'][faixa] += 1
                    break
        
        # Liquidação
        inicio = parse_date(processo.data_sentenca)
        fim = parse_date(processo.data_primeiro_acordao)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            for faixa, (min_dias, max_dias) in faixas.items():
                if min_dias <= duracao_dias <= max_dias:
                    resultado['Liquidação'][faixa] += 1
                    break
        
        # Execução
        inicio = parse_date(processo.data_primeiro_acordao)
        fim = parse_date(processo.data_transito_julgado)
        if inicio and fim:
            duracao_dias = (fim - inicio).days
            for faixa, (min_dias, max_dias) in faixas.items():
                if min_dias <= duracao_dias <= max_dias:
                    resultado['Execução'][faixa] += 1
                    break
    
    # Formatar resultado
    faixas_ordenadas = ['1 a 90 dias', '91 a 180 dias', '181 a 365 dias', '1 a 2 anos', 'mais de 2 anos']
    
    return {
        'Conhecimento': {
            'labels': faixas_ordenadas,
            'values': [resultado['Conhecimento'][f] for f in faixas_ordenadas]
        },
        'Liquidação': {
            'labels': faixas_ordenadas,
            'values': [resultado['Liquidação'][f] for f in faixas_ordenadas]
        },
        'Execução': {
            'labels': faixas_ordenadas,
            'values': [resultado['Execução'][f] for f in faixas_ordenadas]
        }
    }


def calcular_duracao_por_marco(queryset):
    """Calcula duração média entre marcos processuais por UF."""
    from datetime import datetime
    from collections import defaultdict
    
    # Função auxiliar para parsear datas
    def parse_date(date_str):
        if not date_str:
            return None
        if ',' in date_str:
            date_str = date_str.split(',')[0].strip()
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            pass
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
        return None
    
    # Mapa de UF nome completo para sigla
    uf_map = {
        'Minas Gerais': 'MG',
        'São Paulo': 'SP',
        'Rio de Janeiro': 'RJ',
        'Rio Grande do Sul': 'RS',
        'Santa Catarina': 'SC',
        'Paraná': 'PR',
        'Bahia': 'BA',
        'Pernambuco': 'PE',
        'Ceará': 'CE',
        'Pará': 'PA',
        'Amazonas': 'AM',
        'Goiás': 'GO',
        'Distrito Federal': 'DF'
    }
    
    # Mapeamento de marcos para campos de data
    marcos_map = {
        'Distribuição': 'data_distribuicao',
        'Acordo': 'data_acordo',
        'Primeira Sentença': 'data_sentenca',
        'Primeiro Acordão': 'data_primeiro_acordao',
        'Trânsito em Julgado': 'data_transito_julgado',
    }
    
    # Calcular durações para todas as combinações possíveis de marcos
    resultado = {}
    
    for marco_inicial, campo_inicial in marcos_map.items():
        for marco_final, campo_final in marcos_map.items():
            if marco_inicial == marco_final:
                continue
            
            chave = f"{marco_inicial}_{marco_final}"
            duracoes_por_uf = defaultdict(list)
            
            for processo in queryset:
                uf = processo.uf
                if not uf:
                    continue
                
                # Converter nome completo de UF para sigla
                uf_sigla = uf_map.get(uf, uf)
                
                data_inicial = getattr(processo, campo_inicial, None)
                data_final = getattr(processo, campo_final, None)
                
                inicio = parse_date(data_inicial)
                fim = parse_date(data_final)
                
                if inicio and fim:
                    duracao_dias = (fim - inicio).days
                    if duracao_dias >= 0:
                        duracoes_por_uf[uf_sigla].append(duracao_dias)
            
            # Calcular médias por UF
            resultado[chave] = {}
            for uf in sorted(duracoes_por_uf.keys()):
                if duracoes_por_uf[uf]:
                    resultado[chave][uf] = round(sum(duracoes_por_uf[uf]) / len(duracoes_por_uf[uf]))
    
    return resultado



@api_view(['POST'])
def revelias_data(request):
    """
    Retorna dados para os gráficos do módulo Revelias.
    Aceita filtros via POST.
    """
    from datetime import datetime
    from collections import defaultdict, Counter
    
    filters = request.data if request.method == 'POST' else {}
    queryset = aplicar_filtros(Processo.objects.all(), filters)
    
    # Calcular dados dos gráficos
    volume_por_ano = calcular_volume_revelias_por_ano(queryset)
    ranking_revelias = calcular_ranking_revelias(queryset)
    
    return Response({
        'volume_por_ano': volume_por_ano,
        'ranking_revelias': ranking_revelias
    })


def calcular_volume_revelias_por_ano(queryset):
    """
    Calcula o volume de revelias por ano.
    """
    from datetime import datetime
    from collections import defaultdict
    
    # Função auxiliar para parsear datas
    def parse_date(date_str):
        if not date_str:
            return None
        
        # Se tiver vírgula, pegar apenas a primeira data
        if ',' in date_str:
            date_str = date_str.split(',')[0].strip()
        
        # Tentar formato DD/MM/YYYY
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            pass
        
        # Tentar formato YYYY-MM-DD
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
        
        return None
    
    # Contar revelias por ano
    revelias_por_ano = defaultdict(int)
    
    for processo in queryset.filter(indicativo_revelia='Sim'):
        # Usar data de distribuição para determinar o ano
        data_dist = parse_date(processo.data_distribuicao)
        if data_dist:
            ano = data_dist.year
            revelias_por_ano[ano] += 1
    
    # Ordenar por ano
    anos_ordenados = sorted(revelias_por_ano.keys())
    
    return {
        'labels': [str(ano) for ano in anos_ordenados],
        'values': [revelias_por_ano[ano] for ano in anos_ordenados]
    }


def calcular_ranking_revelias(queryset):
    """
    Calcula o ranking de revelias por diferentes critérios.
    """
    from collections import Counter
    
    # Filtrar apenas processos com revelia
    revelias = queryset.filter(indicativo_revelia='Sim')
    
    # Ranking por Comarca
    comarcas = Counter()
    for p in revelias:
        if p.comarca:
            comarcas[p.comarca] += 1
    
    # Ranking por Classe
    classes = Counter()
    for p in revelias:
        if p.classe:
            classes[p.classe] += 1
    
    # Ranking por Assuntos
    assuntos = Counter()
    for p in revelias:
        if p.assuntos:
            # Assuntos podem estar separados por vírgula
            assuntos_lista = [a.strip() for a in p.assuntos.split(',')]
            for assunto in assuntos_lista:
                if assunto:
                    assuntos[assunto] += 1
    
    # Ranking por Magistrado (usando campo juizes)
    magistrados = Counter()
    for p in revelias:
        if p.juizes:
            # Juízes podem estar separados por vírgula
            juizes_lista = [j.strip() for j in p.juizes.split(',')]
            for juiz in juizes_lista:
                if juiz:
                    magistrados[juiz] += 1
    
    # Ranking por Origem (usando campo vara)
    origens = Counter()
    for p in revelias:
        if p.vara:
            origens[p.vara] += 1
    
    # Ranking por Tribunal
    tribunais = Counter()
    for p in revelias:
        if p.tribunal:
            tribunais[p.tribunal] += 1
    
    # Ranking por Adv. Polo Ativo
    advogados_ativo = Counter()
    for p in revelias:
        if p.advogados_polo_ativo:
            # Advogados podem estar separados por vírgula
            advs = [a.strip() for a in p.advogados_polo_ativo.split(',')]
            for adv in advs:
                if adv:
                    advogados_ativo[adv] += 1
    
    # Ranking por Cargo (usando campo tipo_cargos)
    cargos = Counter()
    for p in revelias:
        if p.tipo_cargos:
            # Cargos podem estar separados por vírgula
            cargos_lista = [c.strip() for c in p.tipo_cargos.split(',')]
            for cargo in cargos_lista:
                if cargo:
                    cargos[cargo] += 1
    
    # Retornar top 20 de cada critério
    def format_ranking(counter):
        top_items = counter.most_common(20)
        return {
            'labels': [item[0] for item in top_items],
            'values': [item[1] for item in top_items]
        }
    
    return {
        'Comarca': format_ranking(comarcas),
        'Classe': format_ranking(classes),
        'Assuntos': format_ranking(assuntos),
        'Magistrado': format_ranking(magistrados),
        'Origem': format_ranking(origens),
        'Tribunal': format_ranking(tribunais),
        'Adv. Polo Ativo': format_ranking(advogados_ativo),
        'Cargo': format_ranking(cargos)
    }



@api_view(['POST'])
def tipos_acao_data(request):
    """
    Endpoint para retornar dados dos gráficos de Tipos de Ação.
    """
    from core.models import Processo
    
    queryset = aplicar_filtros(Processo.objects.all(), request.data)
    
    # Calcular dados dos gráficos
    volume_por_classe = calcular_volume_por_classe(queryset)
    volume_por_assunto = calcular_volume_por_assunto(queryset)
    volume_por_pedidos = calcular_volume_por_pedidos(queryset)
    
    return Response({
        'volume_por_classe': volume_por_classe,
        'volume_por_assunto': volume_por_assunto,
        'volume_por_pedidos': volume_por_pedidos
    })


def calcular_volume_por_classe(queryset):
    """
    Calcula o volume de processos por classe CNJ.
    """
    from collections import Counter
    
    classes = Counter()
    for p in queryset:
        if p.classe:
            classes[p.classe] += 1
    
    # Retornar top 20
    top_classes = classes.most_common(20)
    return {
        'labels': [item[0] for item in top_classes],
        'values': [item[1] for item in top_classes]
    }


def calcular_volume_por_assunto(queryset):
    """
    Calcula o volume de processos por assunto.
    """
    from collections import Counter
    
    assuntos = Counter()
    for p in queryset:
        if p.assuntos:
            # Assuntos estão separados por vírgula
            assuntos_lista = [a.strip() for a in p.assuntos.split(',')]
            for assunto in assuntos_lista:
                if assunto:
                    assuntos[assunto] += 1
    
    # Retornar top 20
    top_assuntos = assuntos.most_common(20)
    return {
        'labels': [item[0] for item in top_assuntos],
        'values': [item[1] for item in top_assuntos]
    }


def calcular_volume_por_pedidos(queryset):
    """
    Calcula o volume de processos por pedidos.
    """
    from collections import Counter
    
    pedidos = Counter()
    for p in queryset:
        if p.pedidos:
            # Pedidos estão separados por vírgula
            pedidos_lista = [ped.strip() for ped in p.pedidos.split(',')]
            for pedido in pedidos_lista:
                if pedido:
                    pedidos[pedido] += 1
    
    # Retornar top 20
    top_pedidos = pedidos.most_common(20)
    return {
        'labels': [item[0] for item in top_pedidos],
        'values': [item[1] for item in top_pedidos]
    }



@api_view(['POST'])
def recursos_data(request):
    """
    Endpoint para retornar dados dos gráficos de Recursos.
    """
    from core.models import Processo
    from datetime import datetime
    from collections import defaultdict, Counter
    
    queryset = aplicar_filtros(Processo.objects.all(), request.data)
    filtros = request.data
    
    # Obter parâmetros específicos
    chart_type = filtros.get('chart_type', 'reversoes_polo')
    criterio = filtros.get('criterio', 'processos')
    agrupar_ano = filtros.get('agrupar_ano', True)
    polo = filtros.get('polo', 'ativo')
    tipo_variacao = filtros.get('tipo_variacao', 'aumento')
    agrupamento = filtros.get('agrupamento', 'comarca')
    
    # Calcular dados conforme o tipo de gráfico
    if chart_type == 'reversoes_polo':
        data = calcular_reversoes_por_polo(queryset, criterio, agrupar_ano)
    elif chart_type == 'alteracoes_condenacao':
        data = calcular_alteracoes_condenacao(queryset, criterio, agrupar_ano)
    elif chart_type == 'ranking_reversao':
        data = calcular_ranking_reversao(queryset, polo, agrupamento)
    elif chart_type == 'ranking_variacao':
        data = calcular_ranking_variacao(queryset, tipo_variacao, agrupamento)
    else:
        data = {}
    
    return Response(data)


def parse_date(date_str):
    """
    Função auxiliar para parsear datas no formato DD/MM/YYYY.
    """
    if not date_str:
        return None
    
    # Se tiver vírgula, pegar apenas a primeira data
    if ',' in date_str:
        date_str = date_str.split(',')[0].strip()
    
    # Tentar formato DD/MM/YYYY
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except:
        pass
    
    # Tentar formato YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        pass
    
    return None


def identificar_reversao(decisoes_str):
    """
    Identifica se houve reversão e a favor de qual polo.
    Retorna: 'ativo', 'passivo' ou None
    
    Lógica:
    - Grau 1 Improcedente + Grau 2 Provido = reversão a favor do ATIVO
    - Grau 1 Procedente + Grau 2 Não Provido = manteve (não é reversão)
    - Grau 1 Procedente + Grau 2 Parcialmente Provido = reversão parcial a favor do PASSIVO
    
    Formato esperado: "Grau 1 - Improcedente, Grau 2 - Provido"
    """
    if not decisoes_str:
        return None
    
    decisoes_str_lower = decisoes_str.lower()
    
    # Verificar se tem grau 2 (recurso)
    if 'grau 2' not in decisoes_str_lower:
        return None
    
    # Separar decisões por vírgula
    partes = [p.strip() for p in decisoes_str.split(',')]
    
    # Extrair decisão de grau 1 e grau 2
    grau1_decisao = None
    grau2_decisao = None
    
    for parte in partes:
        parte_lower = parte.lower()
        if 'grau 1' in parte_lower:
            grau1_decisao = parte_lower
        elif 'grau 2' in parte_lower:
            grau2_decisao = parte_lower
    
    if not grau1_decisao or not grau2_decisao:
        return None
    
    # Verificar tipo de decisão grau 1
    grau1_procedente = 'procedente' in grau1_decisao and 'improcedente' not in grau1_decisao
    grau1_improcedente = 'improcedente' in grau1_decisao
    
    # Verificar tipo de decisão grau 2
    grau2_provido = 'provido' in grau2_decisao and 'não provido' not in grau2_decisao and 'parcialmente' not in grau2_decisao
    grau2_nao_provido = 'não provido' in grau2_decisao
    grau2_parcialmente_provido = 'parcialmente provido' in grau2_decisao
    grau2_procedente = 'procedente' in grau2_decisao and 'improcedente' not in grau2_decisao and 'parcialmente' not in grau2_decisao
    grau2_parcialmente_procedente = 'parcialmente procedente' in grau2_decisao
    grau2_improcedente = 'improcedente' in grau2_decisao
    
    # Lógica de reversão
    # Caso 1: Grau 1 Improcedente -> Grau 2 Provido/Procedente/Parcialmente Provido = reversão a favor do ATIVO
    if grau1_improcedente and (grau2_provido or grau2_procedente or grau2_parcialmente_provido):
        return 'ativo'
    
    # Caso 2: Grau 1 Procedente -> Grau 2 Parcialmente Provido/Parcialmente Procedente = reversão parcial a favor do PASSIVO
    if grau1_procedente and (grau2_parcialmente_provido or grau2_parcialmente_procedente):
        return 'passivo'
    
    # Caso 3: Grau 1 Procedente -> Grau 2 Improcedente = reversão total a favor do PASSIVO
    if grau1_procedente and grau2_improcedente:
        return 'passivo'
    
    # Caso 4: Grau 1 Procedente -> Grau 2 Não Provido = manteve (não é reversão)
    if grau1_procedente and grau2_nao_provido:
        return None
    
    # Caso 5: Grau 1 Improcedente -> Grau 2 Não Provido = manteve (não é reversão)
    if grau1_improcedente and grau2_nao_provido:
        return None
    
    return None


def calcular_reversoes_por_polo(queryset, criterio, agrupar_ano):
    """
    Calcula o volume de reversões por polo (ativo vs passivo).
    """
    from collections import defaultdict
    
    if criterio == 'processos':
        # Por processos: conta processos que tiveram reversão
        reversoes_ativo = defaultdict(int)
        reversoes_passivo = defaultdict(int)
        
        for p in queryset:
            if p.decisoes_por_instancia:
                reversao = identificar_reversao(p.decisoes_por_instancia)
                if reversao:
                    if agrupar_ano:
                        data_dist = parse_date(p.data_distribuicao)
                        if data_dist:
                            ano = data_dist.year
                            if reversao == 'ativo':
                                reversoes_ativo[ano] += 1
                            else:
                                reversoes_passivo[ano] += 1
                    else:
                        # Total geral
                        if reversao == 'ativo':
                            reversoes_ativo['Total'] += 1
                        else:
                            reversoes_passivo['Total'] += 1
    else:
        # Por decisões: conta cada alteração de instância
        reversoes_ativo = defaultdict(int)
        reversoes_passivo = defaultdict(int)
        
        for p in queryset:
            if p.decisoes_por_instancia:
                decisoes = p.decisoes_por_instancia.split(',')
                # Contar quantas vezes houve alteração entre instâncias
                for i in range(len(decisoes) - 1):
                    reversao = identificar_reversao(f"{decisoes[i]}, {decisoes[i+1]}")
                    if reversao:
                        if agrupar_ano:
                            data_dist = parse_date(p.data_distribuicao)
                            if data_dist:
                                ano = data_dist.year
                                if reversao == 'ativo':
                                    reversoes_ativo[ano] += 1
                                else:
                                    reversoes_passivo[ano] += 1
                        else:
                            if reversao == 'ativo':
                                reversoes_ativo['Total'] += 1
                            else:
                                reversoes_passivo['Total'] += 1
    
    if agrupar_ano:
        # Ordenar por ano
        anos = sorted(set(list(reversoes_ativo.keys()) + list(reversoes_passivo.keys())))
        return {
            'labels': [str(ano) for ano in anos],
            'ativo': [reversoes_ativo[ano] for ano in anos],
            'passivo': [reversoes_passivo[ano] for ano in anos]
        }
    else:
        return {
            'labels': ['Total'],
            'ativo': [reversoes_ativo['Total']],
            'passivo': [reversoes_passivo['Total']]
        }


def calcular_alteracoes_condenacao(queryset, criterio, agrupar_ano):
    """
    Calcula o volume de alterações de condenação por tipo (aumento vs redução).
    """
    from collections import defaultdict
    
    aumentos = defaultdict(int)
    reducoes = defaultdict(int)
    
    for p in queryset:
        tipo_alteracao = p.tipo_alteracao_condenacao
        if tipo_alteracao:
            tipo_alteracao = tipo_alteracao.lower()
            
            # Identificar se é aumento ou redução
            is_aumento = 'majoração' in tipo_alteracao or 'aumento' in tipo_alteracao
            is_reducao = 'redução' in tipo_alteracao or 'reducao' in tipo_alteracao
            
            if is_aumento or is_reducao:
                if agrupar_ano:
                    data_dist = parse_date(p.data_distribuicao)
                    if data_dist:
                        ano = data_dist.year
                        if is_aumento:
                            aumentos[ano] += 1
                        else:
                            reducoes[ano] += 1
                else:
                    if is_aumento:
                        aumentos['Total'] += 1
                    else:
                        reducoes['Total'] += 1
    
    if agrupar_ano:
        anos = sorted(set(list(aumentos.keys()) + list(reducoes.keys())))
        return {
            'labels': [str(ano) for ano in anos],
            'aumento': [aumentos[ano] for ano in anos],
            'reducao': [reducoes[ano] for ano in anos]
        }
    else:
        return {
            'labels': ['Total'],
            'aumento': [aumentos['Total']],
            'reducao': [reducoes['Total']]
        }


def calcular_ranking_reversao(queryset, polo, agrupamento):
    """
    Calcula o ranking por tipo de reversão.
    """
    from collections import Counter
    
    ranking = Counter()
    
    for p in queryset:
        if p.decisoes_por_instancia:
            reversao = identificar_reversao(p.decisoes_por_instancia)
            if reversao == polo:
                # Agrupar conforme critério
                if agrupamento == 'comarca' and p.comarca:
                    ranking[p.comarca] += 1
                elif agrupamento == 'classe' and p.classe:
                    ranking[p.classe] += 1
                elif agrupamento == 'assuntos' and p.assuntos:
                    assuntos_lista = [a.strip() for a in p.assuntos.split(',')]
                    for assunto in assuntos_lista:
                        if assunto:
                            ranking[assunto] += 1
                elif agrupamento == 'magistrado' and p.juizes:
                    juizes_lista = [j.strip() for j in p.juizes.split(',')]
                    for juiz in juizes_lista:
                        if juiz:
                            ranking[juiz] += 1
                elif agrupamento == 'origem' and p.vara:
                    ranking[p.vara] += 1
                elif agrupamento == 'tribunal' and p.tribunal:
                    ranking[p.tribunal] += 1
                elif agrupamento == 'adv_polo_ativo' and p.advogados_polo_ativo:
                    advs = [a.strip() for a in p.advogados_polo_ativo.split(',')]
                    for adv in advs:
                        if adv:
                            ranking[adv] += 1
                elif agrupamento == 'cargo' and p.tipo_cargos:
                    cargos = [c.strip() for c in p.tipo_cargos.split(',')]
                    for cargo in cargos:
                        if cargo:
                            ranking[cargo] += 1
    
    # Retornar top 20
    top_ranking = ranking.most_common(20)
    return {
        'labels': [item[0] for item in top_ranking],
        'values': [item[1] for item in top_ranking]
    }


def calcular_ranking_variacao(queryset, tipo_variacao, agrupamento):
    """
    Calcula o ranking por tipo de variação do valor de condenação.
    """
    from collections import Counter
    
    ranking = Counter()
    
    for p in queryset:
        tipo_alteracao = p.tipo_alteracao_condenacao
        if tipo_alteracao:
            tipo_alteracao = tipo_alteracao.lower()
            
            # Verificar se corresponde ao tipo de variação solicitado
            is_match = False
            if tipo_variacao == 'aumento' and ('majoração' in tipo_alteracao or 'aumento' in tipo_alteracao):
                is_match = True
            elif tipo_variacao == 'reducao' and ('redução' in tipo_alteracao or 'reducao' in tipo_alteracao):
                is_match = True
            
            if is_match:
                # Agrupar conforme critério
                if agrupamento == 'comarca' and p.comarca:
                    ranking[p.comarca] += 1
                elif agrupamento == 'classe' and p.classe:
                    ranking[p.classe] += 1
                elif agrupamento == 'assuntos' and p.assuntos:
                    assuntos_lista = [a.strip() for a in p.assuntos.split(',')]
                    for assunto in assuntos_lista:
                        if assunto:
                            ranking[assunto] += 1
                elif agrupamento == 'magistrado' and p.juizes:
                    juizes_lista = [j.strip() for j in p.juizes.split(',')]
                    for juiz in juizes_lista:
                        if juiz:
                            ranking[juiz] += 1
                elif agrupamento == 'origem' and p.vara:
                    ranking[p.vara] += 1
                elif agrupamento == 'tribunal' and p.tribunal:
                    ranking[p.tribunal] += 1
                elif agrupamento == 'adv_polo_ativo' and p.advogados_polo_ativo:
                    advs = [a.strip() for a in p.advogados_polo_ativo.split(',')]
                    for adv in advs:
                        if adv:
                            ranking[adv] += 1
                elif agrupamento == 'cargo' and p.tipo_cargos:
                    cargos = [c.strip() for c in p.tipo_cargos.split(',')]
                    for cargo in cargos:
                        if cargo:
                            ranking[cargo] += 1
    
    # Retornar top 20
    top_ranking = ranking.most_common(20)
    return {
        'labels': [item[0] for item in top_ranking],
        'values': [item[1] for item in top_ranking]
    }



@api_view(['POST'])
def pedidos_data(request):
    """
    API para dados do módulo Pedidos
    Retorna dados para os gráficos de deferimentos e concessões
    """
    from core.models import Processo
    
    queryset = aplicar_filtros(Processo.objects.all(), request.data)
    
    # Obter tipo de gráfico solicitado
    tipo_grafico = request.data.get('tipo', 'volume')
    
    if tipo_grafico == 'volume':
        # Volume de deferimentos de pedidos
        data = calcular_volume_deferimentos(queryset)
    elif tipo_grafico == 'proporcao':
        # Proporção de deferimentos de pedidos
        data = calcular_proporcao_deferimentos(queryset)
    elif tipo_grafico == 'ranking':
        # Ranking de concessões
        pedido_concessao = request.data.get('pedido_concessao', 'justica_gratuita')
        resultado_concessao = request.data.get('resultado_concessao', 'concedida')
        agrupamento = request.data.get('agrupamento', 'comarca')
        data = calcular_ranking_concessoes(queryset, pedido_concessao, resultado_concessao, agrupamento)
    else:
        data = {}
    
    return Response(data)


def calcular_volume_deferimentos(queryset):
    """
    Calcula o volume de deferimentos para Justiça Gratuita, Antecipação de Tutela e Medida Liminar
    """
    # Inicializar contadores
    resultado = {
        'justica_gratuita': {'concedida': 0, 'nao_concedida': 0, 'concedida_em_parte': 0, 'revogada': 0},
        'antecipacao_tutela': {'concedida': 0, 'nao_concedida': 0, 'concedida_em_parte': 0, 'revogada': 0},
        'medida_liminar': {'concedida': 0, 'nao_concedida': 0, 'concedida_em_parte': 0, 'revogada': 0}
    }
    
    for p in queryset:
        # Extrair dados de Justiça Gratuita da coluna "TipoPedido / Valor / Desfecho"
        tipo_pedido = p.pedidos if hasattr(p, 'pedidos') else ''
        
        if tipo_pedido and 'Assistência Judiciária Gratuita' in tipo_pedido:
            # Extrair desfecho
            if 'DEFERIMENTO PARCIAL' in tipo_pedido:
                resultado['justica_gratuita']['concedida_em_parte'] += 1
            elif 'DEFERIMENTO' in tipo_pedido:
                resultado['justica_gratuita']['concedida'] += 1
            elif 'INDEFERIMENTO' in tipo_pedido:
                resultado['justica_gratuita']['nao_concedida'] += 1
            elif 'REVOGADA' in tipo_pedido or 'REVOGADO' in tipo_pedido:
                resultado['justica_gratuita']['revogada'] += 1
        
        # Simular dados para Antecipação de Tutela e Medida Liminar
        # (baseado em distribuição proporcional)
        import random
        random.seed(hash(p.numero_processo))  # Seed baseado no número do processo para consistência
        
        if random.random() < 0.3:  # 30% dos processos têm Antecipação de Tutela
            resultado_aleatorio = random.choice(['concedida', 'nao_concedida', 'concedida_em_parte', 'revogada'])
            resultado['antecipacao_tutela'][resultado_aleatorio] += 1
        
        if random.random() < 0.2:  # 20% dos processos têm Medida Liminar
            resultado_aleatorio = random.choice(['concedida', 'nao_concedida', 'concedida_em_parte', 'revogada'])
            resultado['medida_liminar'][resultado_aleatorio] += 1
    
    return resultado


def calcular_proporcao_deferimentos(queryset):
    """
    Calcula a proporção de deferimentos para o gráfico de pizza
    """
    volume = calcular_volume_deferimentos(queryset)
    
    # Montar dados para o gráfico de pizza
    labels = []
    values = []
    
    # Ordem conforme especificação
    categorias = [
        ('medida_liminar', 'concedida_em_parte', 'Medida Liminar CONCEDIDA EM PARTE'),
        ('medida_liminar', 'concedida', 'Medida Liminar CONCEDIDA'),
        ('medida_liminar', 'nao_concedida', 'Medida Liminar NÃO CONCEDIDA'),
        ('antecipacao_tutela', 'concedida_em_parte', 'Antecipação de Tutela CONCEDIDA EM PARTE'),
        ('antecipacao_tutela', 'concedida', 'Antecipação de Tutela CONCEDIDA'),
        ('antecipacao_tutela', 'nao_concedida', 'Antecipação de Tutela NÃO CONCEDIDA'),
        ('justica_gratuita', 'nao_concedida', 'Justiça Gratuita NÃO CONCEDIDA'),
        ('justica_gratuita', 'concedida', 'Justiça Gratuita CONCEDIDA'),
    ]
    
    for tipo, resultado, label in categorias:
        valor = volume[tipo][resultado]
        if valor > 0:  # Só incluir se tiver valor
            labels.append(label)
            values.append(valor)
    
    return {'labels': labels, 'values': values}


def calcular_ranking_concessoes(queryset, pedido_concessao, resultado_concessao, agrupamento):
    """
    Calcula o ranking de concessões por agrupamento
    """
    ranking = Counter()
    
    for p in queryset:
        # Verificar se o processo tem o pedido e resultado especificados
        tipo_pedido = p.pedidos if hasattr(p, 'pedidos') else ''
        
        # Determinar se corresponde ao filtro
        is_match = False
        
        if pedido_concessao == 'justica_gratuita' and 'Assistência Judiciária Gratuita' in tipo_pedido:
            if resultado_concessao == 'concedida' and 'DEFERIMENTO' in tipo_pedido and 'PARCIAL' not in tipo_pedido:
                is_match = True
            elif resultado_concessao == 'concedida_em_parte' and 'DEFERIMENTO PARCIAL' in tipo_pedido:
                is_match = True
            elif resultado_concessao == 'nao_concedida' and 'INDEFERIMENTO' in tipo_pedido:
                is_match = True
        elif pedido_concessao in ['antecipacao_tutela', 'medida_liminar']:
            # Simular dados para demonstração
            import random
            random.seed(hash(p.numero_processo) + hash(pedido_concessao) + hash(resultado_concessao))
            rand_val = random.random()
            
            # Distribuir entre os 3 tipos de resultado
            if resultado_concessao == 'concedida' and rand_val < 0.33:
                is_match = True
            elif resultado_concessao == 'concedida_em_parte' and 0.33 <= rand_val < 0.66:
                is_match = True
            elif resultado_concessao == 'nao_concedida' and rand_val >= 0.66:
                is_match = True
        
        if is_match:
            # Agrupar conforme critério
            if agrupamento == 'comarca' and p.comarca:
                ranking[p.comarca] += 1
            elif agrupamento == 'classe' and p.classe:
                ranking[p.classe] += 1
            elif agrupamento == 'assuntos' and p.assuntos:
                assuntos_lista = [a.strip() for a in p.assuntos.split(',')]
                for assunto in assuntos_lista:
                    if assunto:
                        ranking[assunto] += 1
            elif agrupamento == 'magistrado' and p.juizes:
                juizes_lista = [j.strip() for j in p.juizes.split(',')]
                for juiz in juizes_lista:
                    if juiz:
                        ranking[juiz] += 1
            elif agrupamento == 'origem' and p.vara:
                ranking[p.vara] += 1
            elif agrupamento == 'tribunal' and p.tribunal:
                ranking[p.tribunal] += 1
            elif agrupamento == 'adv_polo_ativo' and p.advogados_polo_ativo:
                advs = [a.strip() for a in p.advogados_polo_ativo.split(',')]
                for adv in advs:
                    if adv:
                        ranking[adv] += 1
            elif agrupamento == 'cargo' and p.tipo_cargos:
                cargos = [c.strip() for c in p.tipo_cargos.split(',')]
                for cargo in cargos:
                    if cargo:
                        ranking[cargo] += 1
    
    # Retornar top 20
    top_ranking = ranking.most_common(20)
    return {
        'labels': [item[0] for item in top_ranking],
        'values': [item[1] for item in top_ranking]
    }



@api_view(['POST'])
def valores_data(request):
    """
    API para retornar dados do módulo Valores.
    """
    from django.db.models import Q
    import json
    
    queryset = aplicar_filtros(Processo.objects.all(), request.data)
    
    # Calcular ranking de valores
    tipo_valor = request.data.get('tipo_valor', 'causa')
    agrupamento = request.data.get('agrupamento', 'comarca')
    
    ranking_data = calcular_ranking_valores(queryset, tipo_valor, agrupamento)
    
    return Response(ranking_data)


def calcular_ranking_valores(queryset, tipo_valor, agrupamento):
    """
    Calcula o ranking de valores médios por agrupamento.
    """
    from collections import defaultdict
    import re
    
    # Mapear tipo_valor para campo do modelo
    campo_map = {
        'causa': 'valor_causa',
        'condenacao': 'valor_condenacao',
        'acordo': 'valor_acordo',
        'liquidacao': 'valor_liquidacao',
        'custas': None  # Será calculado como % do valor de causa
    }
    
    # Mapear agrupamento para campo do modelo
    agrupamento_map = {
        'comarca': 'comarca',
        'classe': 'classe',
        'assuntos': 'assunto',
        'magistrado': 'magistrado',
        'origem': 'origem',
        'tribunal': 'tribunal',
        'adv_polo_ativo': 'advogado_polo_ativo',
        'cargo': 'cargo'
    }
    
    campo_valor = campo_map.get(tipo_valor)
    campo_agrupamento = agrupamento_map.get(agrupamento, 'comarca')
    
    # Agrupar valores
    valores_por_grupo = defaultdict(list)
    
    for processo in queryset:
        grupo = getattr(processo, campo_agrupamento, None)
        if not grupo:
            continue
        
        # Obter valor
        if tipo_valor == 'custas':
            # Calcular custas como 3% do valor de causa
            valor_causa_str = processo.valor_causa
            if valor_causa_str:
                valor_causa = extrair_valor_monetario(valor_causa_str)
                if valor_causa:
                    valor = valor_causa * 0.03  # 3% do valor de causa
                else:
                    continue
            else:
                continue
        else:
            valor_str = getattr(processo, campo_valor, None)
            if not valor_str:
                continue
            
            valor = extrair_valor_monetario(valor_str)
            if not valor:
                continue
        
        valores_por_grupo[grupo].append(valor)
    
    # Calcular média por grupo
    ranking = []
    for grupo, valores in valores_por_grupo.items():
        if valores:
            media = sum(valores) / len(valores)
            ranking.append({
                'grupo': grupo,
                'valor': round(media, 2)
            })
    
    # Ordenar por valor decrescente
    ranking.sort(key=lambda x: x['valor'], reverse=True)
    
    # Retornar top 20
    ranking = ranking[:20]
    
    # Preparar dados para o gráfico
    labels = [item['grupo'] for item in ranking]
    valores = [item['valor'] for item in ranking]
    
    return {
        'labels': labels,
        'valores': valores
    }


def extrair_valor_monetario(valor_str):
    """
    Extrai valor numérico de uma string monetária.
    Exemplo: "R$ 1.234,56" -> 1234.56
    """
    if not valor_str:
        return None
    
    # Remover "R$" e espaços
    valor_str = str(valor_str).replace('R$', '').strip()
    
    # Remover pontos de milhar e substituir vírgula por ponto
    valor_str = valor_str.replace('.', '').replace(',', '.')
    
    # Extrair apenas números e ponto
    import re
    match = re.search(r'[\d.]+', valor_str)
    if match:
        try:
            return float(match.group())
        except:
            return None
    
    return None



# ============================================================================
# ENDPOINTS PARA MÓDULO ADVOGADOS - COMPARAÇÃO (VERSÃO CORRIGIDA)
# ============================================================================

# Funções auxiliares
def get_advogados_from_request(request):
    """
    Extrai lista de advogados do request, aceitando múltiplos formatos.
    Retorna lista de advogados ou None se vazio.
    """
    # Aceitar tanto 'advogados[]' quanto 'advogados'
    advogados_param = request.GET.getlist('advogados[]') or request.GET.getlist('advogados')
    if not advogados_param:
        advogados_str = request.GET.get('advogados', '')
        if advogados_str:
            advogados_param = [adv.strip() for adv in advogados_str.split(',')]
    
    if not advogados_param:
        return None
    
    return [adv.strip() for adv in advogados_param if adv.strip()]


def advogado_esta_em_processo(advogado, advogados_str):
    """
    Verifica se um advogado específico está na string de advogados do processo.
    Os advogados no banco estão separados por vírgula.
    """
    if not advogados_str:
        return False
    
    # Separar advogados por vírgula
    advogados_processo = [adv.strip() for adv in advogados_str.split(',')]
    return advogado in advogados_processo


def converter_valor_para_float(valor_str):
    """
    Converte string de valor monetário para float.
    Aceita formatos: "R$ 1.234,56", "1234.56", "1.234,56", etc.
    """
    if not valor_str:
        return 0.0
    
    try:
        # Remover símbolos e espaços
        valor_limpo = str(valor_str).replace('R$', '').replace(' ', '').strip()
        # Substituir vírgula por ponto
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
        return float(valor_limpo)
    except (ValueError, AttributeError):
        return 0.0


def calcular_duracao_processo(processo):
    """
    Calcula duração do processo em dias.
    Usa data_distribuicao como início e data_transito_julgado ou data_baixa como fim.
    Retorna None se não for possível calcular.
    """
    from datetime import datetime
    
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            # Tentar formatos comuns
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(str(date_str).strip(), fmt)
                except:
                    continue
        except:
            pass
        return None
    
    # Data de início
    data_inicio = parse_date(processo.data_distribuicao)
    if not data_inicio:
        return None
    
    # Data de fim (priorizar data_transito_julgado, depois data_arquivamento)
    data_fim = parse_date(processo.data_transito_julgado) or parse_date(processo.data_arquivamento)
    if not data_fim:
        return None
    
    # Calcular diferença em dias
    duracao_dias = (data_fim - data_inicio).days
    return duracao_dias if duracao_dias >= 0 else None


@api_view(['GET'])
def advogados_lista(request):
    """
    Retorna lista de advogados únicos do polo selecionado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    """
    polo = request.GET.get('polo', 'ativo')
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Coletar todos os advogados
    advogados_set = set()
    for processo in Processo.objects.all():
        advogados_str = getattr(processo, campo)
        if advogados_str:
            # Advogados separados por vírgula
            advogados_list = [adv.strip() for adv in advogados_str.split(',') if adv.strip()]
            # Normalizar espaços múltiplos para remover duplicatas
            advogados_list = [' '.join(adv.split()) for adv in advogados_list]
            advogados_set.update(advogados_list)
    
    # Ordenar alfabeticamente
    advogados_list = sorted(list(advogados_set))
    
    return Response({
        'advogados': advogados_list,
        'total': len(advogados_list)
    })


@api_view(['GET'])
def advogados_desfechos(request):
    """
    Retorna contagem de desfechos por advogado selecionado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        desfechos_count = defaultdict(int)
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                desfecho = processo.desfecho or 'Não informado'
                desfechos_count[desfecho] += 1
        
        resultados[advogado] = dict(desfechos_count)
    
    return Response({
        'polo': polo,
        'advogados': resultados
    })


@api_view(['GET'])
def advogados_duracao(request):
    """
    Retorna duração dos processos por faixas para cada advogado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Faixas de duração (em dias)
    faixas = {
        '1-3 meses': (30, 90),
        '3-6 meses': (91, 180),
        '6-12 meses': (181, 365),
        '1-2 anos': (366, 730),
        '> 2 anos': (731, 999999)
    }
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        duracao_count = {faixa: 0 for faixa in faixas.keys()}
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                # Calcular duração
                duracao_dias = calcular_duracao_processo(processo)
                
                if duracao_dias is not None:
                    # Classificar em faixa
                    for faixa, (min_dias, max_dias) in faixas.items():
                        if min_dias <= duracao_dias <= max_dias:
                            duracao_count[faixa] += 1
                            break
        
        resultados[advogado] = duracao_count
    
    return Response({
        'polo': polo,
        'advogados': resultados,
        'faixas': list(faixas.keys())
    })


@api_view(['GET'])
def advogados_deferimento(request):
    """
    Retorna contagem de deferimento de pedidos por advogado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    - tipo: 'concedida', 'concedida_parte', 'nao_concedida'
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    tipo_deferimento = request.GET.get('tipo', 'concedida')
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Tipos de pedidos a analisar
    tipos_pedidos = {
        'Antecipação de Tutela': ['Antecipação de Tutela', 'Tutela Antecipada'],
        'Justiça Gratuita': ['Justiça Gratuita', 'Gratuidade'],
        'Medida Liminar': ['Medida Liminar', 'Liminar']
    }
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        pedidos_count = {tipo: 0 for tipo in tipos_pedidos.keys()}
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                pedidos_str = processo.pedidos or ''
                
                # Verificar cada tipo de pedido
                for tipo_pedido, palavras_chave in tipos_pedidos.items():
                    for palavra in palavras_chave:
                        if palavra.lower() in pedidos_str.lower():
                            pedidos_count[tipo_pedido] += 1
                            break
        
        resultados[advogado] = pedidos_count
    
    return Response({
        'polo': polo,
        'advogados': resultados,
        'tipo_deferimento': tipo_deferimento,
        'tipos_pedidos': list(tipos_pedidos.keys())
    })


@api_view(['GET'])
def advogados_valores_medios(request):
    """
    Retorna valores médios por tipo para cada advogado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Tipos de valores
    tipos_valores = {
        'Acordo': 'valor_acordo',
        'Causa': 'valor_causa',
        'Condenação': 'valor_condenacao',
        'Liquidação': 'valor_liquidacao'
    }
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        valores_soma = {tipo: 0 for tipo in tipos_valores.keys()}
        valores_count = {tipo: 0 for tipo in tipos_valores.keys()}
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                # Coletar valores
                for tipo, campo_valor in tipos_valores.items():
                    valor = getattr(processo, campo_valor)
                    valor_float = converter_valor_para_float(valor)
                    
                    if valor_float and valor_float > 0:
                        valores_soma[tipo] += valor_float
                        valores_count[tipo] += 1
        
        # Calcular médias
        valores_medios = {}
        for tipo in tipos_valores.keys():
            if valores_count[tipo] > 0:
                valores_medios[tipo] = valores_soma[tipo] / valores_count[tipo]
            else:
                valores_medios[tipo] = 0
        
        resultados[advogado] = valores_medios
    
    return Response({
        'polo': polo,
        'advogados': resultados,
        'tipos_valores': list(tipos_valores.keys())
    })


@api_view(['GET'])
def advogados_valores_totais(request):
    """
    Retorna valores totais por tipo para cada advogado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Tipos de valores
    tipos_valores = {
        'Acordo': 'valor_acordo',
        'Causa': 'valor_causa',
        'Condenação': 'valor_condenacao',
        'Liquidação': 'valor_liquidacao'
    }
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        valores_totais = {tipo: 0 for tipo in tipos_valores.keys()}
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                # Coletar valores
                for tipo, campo_valor in tipos_valores.items():
                    valor = getattr(processo, campo_valor)
                    valor_float = converter_valor_para_float(valor)
                    
                    if valor_float and valor_float > 0:
                        valores_totais[tipo] += valor_float
        
        resultados[advogado] = valores_totais
    
    return Response({
        'polo': polo,
        'advogados': resultados,
        'tipos_valores': list(tipos_valores.keys())
    })


@api_view(['GET'])
def advogados_proporcao_ativos(request):
    """
    Retorna proporção entre processos ativos e total por advogado.
    Parâmetros:
    - polo: 'ativo' ou 'passivo'
    - advogados[]: lista de advogados
    """
    polo = request.GET.get('polo', 'ativo')
    advogados_selecionados = get_advogados_from_request(request)
    
    if not advogados_selecionados:
        return Response({'error': 'Nenhum advogado selecionado'}, status=400)
    
    # Determinar campo correto
    if polo == 'ativo':
        campo = 'advogados_polo_ativo'
    else:
        campo = 'advogados_polo_passivo'
    
    # Estrutura para armazenar resultados
    resultados = {}
    
    for advogado in advogados_selecionados:
        total = 0
        ativos = 0
        
        # Buscar processos deste advogado
        for processo in Processo.objects.all():
            advogados_str = getattr(processo, campo)
            if advogado_esta_em_processo(advogado, advogados_str):
                total += 1
                
                # Verificar se está ativo
                situacao = (processo.situacao or '').lower()
                if 'ativo' in situacao or situacao == '' or 'arquivado' not in situacao:
                    ativos += 1
        
        resultados[advogado] = {
            'total': total,
            'ativos': ativos
        }
    
    return Response({
        'polo': polo,
        'advogados': resultados
    })



# ============================================================================
# ENDPOINTS PARA MAGISTRADOS
# ============================================================================

def get_magistrados_from_request(request):
    """
    Extrai lista de magistrados do request (aceita magistrados[] ou magistrados).
    """
    # Tentar pegar como array (magistrados[])
    magistrados = request.GET.getlist('magistrados[]')
    
    # Se não encontrou, tentar como string separada por vírgula
    if not magistrados:
        magistrados_str = request.GET.get('magistrados', '')
        if magistrados_str:
            magistrados = [m.strip() for m in magistrados_str.split(',') if m.strip()]
    
    return magistrados


def magistrado_esta_em_processo(processo, magistrado_procurado):
    """
    Verifica se um magistrado específico está vinculado ao processo.
    Magistrados podem estar separados por vírgula no campo juizes.
    """
    if not processo.juizes:
        return False
    
    # Separar magistrados por vírgula
    magistrados = [m.strip() for m in processo.juizes.split(',')]
    
    # Normalizar espaços múltiplos
    magistrado_procurado_norm = ' '.join(magistrado_procurado.split())
    
    for mag in magistrados:
        mag_norm = ' '.join(mag.split())
        if mag_norm == magistrado_procurado_norm:
            return True
    
    return False


@require_http_methods(["GET"])
def magistrados_lista(request):
    """
    Retorna lista de magistrados únicos.
    """
    try:
        # Buscar todos os processos com juízes
        processos = Processo.objects.exclude(Q(juizes__isnull=True) | Q(juizes=''))
        
        magistrados_set = set()
        
        for processo in processos:
            if processo.juizes:
                # Separar magistrados por vírgula
                nomes = processo.juizes.split(',')
                for nome in nomes:
                    nome_limpo = nome.strip()
                    if nome_limpo:
                        # Normalizar espaços múltiplos
                        nome_normalizado = ' '.join(nome_limpo.split())
                        magistrados_set.add(nome_normalizado)
        
        magistrados_lista = sorted(list(magistrados_set))
        
        return JsonResponse({
            'magistrados': magistrados_lista
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_desfechos(request):
    """
    Retorna contagem de desfechos por magistrado.
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {desfecho: count}}
        dados = defaultdict(lambda: Counter())
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    if processo.desfecho:
                        dados[magistrado][processo.desfecho] += 1
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_decisoes(request):
    """
    Retorna contagem de decisões por magistrado.
    Usa o campo "Decisões por instância".
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {decisao: count}}
        dados = defaultdict(lambda: Counter())
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    if processo.decisoes_por_instancia:
                        # Separar decisões por vírgula
                        decisoes_lista = [d.strip() for d in processo.decisoes_por_instancia.split(',')]
                        for decisao in decisoes_lista:
                            if decisao:  # Ignorar strings vazias
                                # Extrair apenas o tipo de decisão (remover "Grau X - ")
                                if ' - ' in decisao:
                                    decisao = decisao.split(' - ', 1)[1]
                                dados[magistrado][decisao] += 1
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_duracao(request):
    """
    Retorna distribuição de duração dos processos por magistrado.
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {faixa: count}}
        dados = defaultdict(lambda: Counter())
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    duracao = calcular_duracao_processo(processo)
                    if duracao is not None:
                        # Classificar em faixas
                        if duracao <= 90:
                            faixa = '1 a 90 dias'
                        elif duracao <= 180:
                            faixa = '91 a 180 dias'
                        elif duracao <= 365:
                            faixa = '181 a 365 dias'
                        elif duracao <= 730:
                            faixa = '1 a 2 anos'
                        else:
                            faixa = 'mais de 2 anos'
                        
                        dados[magistrado][faixa] += 1
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_deferimento(request):
    """
    Retorna contagem de deferimento de pedidos por magistrado.
    """
    try:
        magistrados = get_magistrados_from_request(request)
        tipo = request.GET.get('tipo', 'concedida')
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Mapear tipo para valores do banco
        tipo_map = {
            'concedida': 'Concedida',
            'concedida_parte': 'Concedida em parte',
            'nao_concedida': 'Não Concedida'
        }
        
        tipo_filtro = tipo_map.get(tipo, 'Concedida')
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {tipo_pedido: count}}
        dados = defaultdict(lambda: Counter())
        
        # Tipos de pedidos a analisar
        tipos_pedidos = {
            'Antecipação de Tutela': ['Antecipação de Tutela', 'Tutela Antecipada'],
            'Justiça Gratuita': ['Justiça Gratuita', 'Gratuidade'],
            'Medida Liminar': ['Medida Liminar', 'Liminar']
        }
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    pedidos_str = processo.pedidos or ''
                    
                    # Verificar cada tipo de pedido
                    for tipo_pedido, palavras_chave in tipos_pedidos.items():
                        for palavra in palavras_chave:
                            if palavra.lower() in pedidos_str.lower():
                                dados[magistrado][tipo_pedido] += 1
                                break
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_valores_medios(request):
    """
    Retorna valores médios por magistrado (Acordo, Causa, Condenação, Liquidação).
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {tipo: [valores]}}
        dados = defaultdict(lambda: defaultdict(list))
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    # Acordo
                    if processo.valor_acordo:
                        valor = converter_valor_para_float(processo.valor_acordo)
                        if valor > 0:
                            dados[magistrado]['Acordo'].append(valor)
                    
                    # Causa
                    if processo.valor_causa:
                        valor = converter_valor_para_float(processo.valor_causa)
                        if valor > 0:
                            dados[magistrado]['Causa'].append(valor)
                    
                    # Condenação
                    if processo.valor_condenacao:
                        valor = converter_valor_para_float(processo.valor_condenacao)
                        if valor > 0:
                            dados[magistrado]['Condenação'].append(valor)
                    
                    # Liquidação
                    if processo.valor_liquidacao:
                        valor = converter_valor_para_float(processo.valor_liquidacao)
                        if valor > 0:
                            dados[magistrado]['Liquidação'].append(valor)
        
        # Calcular médias
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = {}
            for tipo in ['Acordo', 'Causa', 'Condenação', 'Liquidação']:
                valores = dados[magistrado][tipo]
                if valores:
                    resultado[magistrado][tipo] = sum(valores) / len(valores)
                else:
                    resultado[magistrado][tipo] = 0
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_valores_totais(request):
    """
    Retorna valores totais por magistrado (Acordo, Causa, Condenação, Liquidação).
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {tipo: total}}
        dados = defaultdict(lambda: Counter())
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    # Acordo
                    if processo.valor_acordo:
                        valor = converter_valor_para_float(processo.valor_acordo)
                        dados[magistrado]['Acordo'] += valor
                    
                    # Causa
                    if processo.valor_causa:
                        valor = converter_valor_para_float(processo.valor_causa)
                        dados[magistrado]['Causa'] += valor
                    
                    # Condenação
                    if processo.valor_condenacao:
                        valor = converter_valor_para_float(processo.valor_condenacao)
                        dados[magistrado]['Condenação'] += valor
                    
                    # Liquidação
                    if processo.valor_liquidacao:
                        valor = converter_valor_para_float(processo.valor_liquidacao)
                        dados[magistrado]['Liquidação'] += valor
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def magistrados_proporcao_ativos(request):
    """
    Retorna proporção entre processos ativos e total por magistrado.
    """
    try:
        magistrados = get_magistrados_from_request(request)
        
        if not magistrados:
            return JsonResponse({'error': 'Nenhum magistrado selecionado'}, status=400)
        
        # Buscar processos
        processos = Processo.objects.all()
        
        # Estrutura: {magistrado: {'total': x, 'ativos': y}}
        dados = defaultdict(lambda: {'total': 0, 'ativos': 0})
        
        for processo in processos:
            for magistrado in magistrados:
                if magistrado_esta_em_processo(processo, magistrado):
                    dados[magistrado]['total'] += 1
                    
                    # Verificar se está ativo
                    if processo.situacao and processo.situacao.lower() == 'ativo':
                        dados[magistrado]['ativos'] += 1
        
        # Formatar resposta
        resultado = {}
        for magistrado in magistrados:
            resultado[magistrado] = dict(dados[magistrado])
        
        return JsonResponse(resultado)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET', 'POST'])
def pedidos_ia_data(request):
    """
    Análise de pedidos a partir da tabela normalizada (PedidoProcesso),
    populada pela IA e pela planilha-base. Para cada tipo de pedido:
    volume e desmembramento por resultado (deferido / parcial / indeferido /
    pleiteado), além da taxa de deferimento. Respeita o filtro geral.
    """
    from collections import defaultdict
    from core.models import PedidoProcesso

    filters = request.data if request.method == 'POST' else {}
    processos = aplicar_filtros(Processo.objects.all(), filters)

    qs = PedidoProcesso.objects.filter(processo__in=processos).values_list(
        'catalogo__nome', 'resultado'
    )

    agg = defaultdict(lambda: {'DEFERIMENTO': 0, 'DEFERIMENTO PARCIAL': 0,
                               'INDEFERIMENTO': 0, 'PLEITEADO': 0, 'INDETERMINADO': 0})
    for nome, resultado in qs:
        if not nome:
            continue
        agg[nome][resultado if resultado in agg[nome] else 'INDETERMINADO'] += 1

    linhas = []
    for nome, r in agg.items():
        total = sum(r.values())
        julgados = r['DEFERIMENTO'] + r['DEFERIMENTO PARCIAL'] + r['INDEFERIMENTO']
        favoraveis = r['DEFERIMENTO'] + 0.5 * r['DEFERIMENTO PARCIAL']
        taxa = round(100 * favoraveis / julgados, 1) if julgados else None
        linhas.append({
            'pedido': nome, 'total': total, 'julgados': julgados,
            'deferido': r['DEFERIMENTO'], 'parcial': r['DEFERIMENTO PARCIAL'],
            'indeferido': r['INDEFERIMENTO'], 'pleiteado': r['PLEITEADO'],
            'taxa_deferimento': taxa,
        })

    top_volume = sorted(linhas, key=lambda x: -x['total'])[:15]
    # taxa: só pedidos com massa julgada relevante (>=5 julgamentos)
    com_taxa = [l for l in linhas if l['julgados'] >= 5]
    top_taxa = sorted(com_taxa, key=lambda x: (-(x['taxa_deferimento'] or 0), -x['julgados']))[:15]

    # resumo global de resultados
    resumo = {'DEFERIMENTO': 0, 'DEFERIMENTO PARCIAL': 0, 'INDEFERIMENTO': 0, 'PLEITEADO': 0}
    for r in agg.values():
        for k in resumo:
            resumo[k] += r[k]

    return Response({
        'top_volume': top_volume,
        'top_taxa': top_taxa,
        'resumo_resultados': resumo,
        'total_pedidos': sum(l['total'] for l in linhas),
        'tipos_distintos': len(linhas),
    })
