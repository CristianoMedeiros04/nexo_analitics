"""
Módulo para processamento de dados e geração de informações para os gráficos do dashboard.
"""
from datetime import datetime, timedelta
from django.db.models import Count, Q
from decimal import Decimal
import re
from .models import Processo


def parse_valor_monetario(valor_str):
    """
    Converte string de valor monetário brasileiro para float.
    Ex: 'R$ 1.234,56' -> 1234.56
    """
    if not valor_str or valor_str == '':
        return 0.0
    
    # Remove 'R$', espaços e pontos (separador de milhar)
    valor_limpo = valor_str.replace('R$', '').replace(' ', '').replace('.', '')
    # Substitui vírgula por ponto (separador decimal)
    valor_limpo = valor_limpo.replace(',', '.')
    
    try:
        return float(valor_limpo)
    except:
        return 0.0


def parse_data_brasileira(data_str):
    """
    Converte string de data brasileira para objeto datetime.
    Ex: '26/06/2025' -> datetime(2025, 6, 26)
    """
    if not data_str or data_str == '':
        return None
    
    try:
        return datetime.strptime(data_str, '%d/%m/%Y')
    except:
        return None


def get_cards_info():
    """
    Retorna informações para os 6 cards do topo do dashboard.
    """
    # Total de processos
    total_processos = Processo.objects.count()
    
    # Data de 30 dias atrás
    data_limite = datetime.now() - timedelta(days=30)
    
    # Processos distribuídos nos últimos 30 dias
    processos_distribuidos = 0
    for p in Processo.objects.exclude(data_distribuicao__isnull=True).exclude(data_distribuicao=''):
        data = parse_data_brasileira(p.data_distribuicao)
        if data and data >= data_limite:
            processos_distribuidos += 1
    
    # Processos arquivados nos últimos 30 dias
    processos_arquivados = 0
    for p in Processo.objects.exclude(data_arquivamento__isnull=True).exclude(data_arquivamento=''):
        data = parse_data_brasileira(p.data_arquivamento)
        if data and data >= data_limite:
            processos_arquivados += 1
    
    # Processos transitados em julgado nos últimos 30 dias
    processos_transitados = 0
    for p in Processo.objects.exclude(data_transito_julgado__isnull=True).exclude(data_transito_julgado=''):
        data = parse_data_brasileira(p.data_transito_julgado)
        if data and data >= data_limite:
            processos_transitados += 1
    
    # Valor total e médio das causas
    valores_causa = []
    for p in Processo.objects.exclude(valor_causa__isnull=True).exclude(valor_causa=''):
        valor = parse_valor_monetario(p.valor_causa)
        if valor > 0:
            valores_causa.append(valor)
    
    valor_total_causas = sum(valores_causa) if valores_causa else 0
    valor_medio_causas = valor_total_causas / len(valores_causa) if valores_causa else 0
    
    return {
        'total_processos': total_processos,
        'distribuidos_30d': processos_distribuidos,
        'arquivados_30d': processos_arquivados,
        'transitados_30d': processos_transitados,
        'valor_total_causas': valor_total_causas,
        'valor_medio_causas': valor_medio_causas,
    }


def get_processos_por_uf():
    """
    Retorna dados de processos por UF para o gráfico de barras e mapa.
    """
    # Agrupa processos por UF
    processos_uf = Processo.objects.values('uf').annotate(
        total=Count('numero_processo')
    ).order_by('-total')
    
    # Formata dados para o gráfico
    labels = []
    values = []
    
    for item in processos_uf:
        if item['uf']:
            labels.append(item['uf'])
            values.append(item['total'])
    
    return {
        'labels': labels,
        'values': values
    }


def get_processos_por_comarca():
    """
    Retorna dados de processos por comarca (todos).
    """
    processos_comarca = Processo.objects.values('comarca').annotate(
        total=Count('numero_processo')
    ).order_by('-total')
    
    labels = []
    values = []
    
    for item in processos_comarca:
        if item['comarca']:
            labels.append(item['comarca'])
            values.append(item['total'])
    
    return {
        'labels': labels,
        'values': values
    }


def get_valor_causa_por_uf():
    """
    Retorna valor médio de causa por UF (todos).
    """
    # Processa manualmente pois valor_causa é string
    valores_por_uf = {}
    
    for p in Processo.objects.exclude(valor_causa__isnull=True).exclude(valor_causa=''):
        if p.uf:
            valor = parse_valor_monetario(p.valor_causa)
            if valor > 0:
                if p.uf not in valores_por_uf:
                    valores_por_uf[p.uf] = []
                valores_por_uf[p.uf].append(valor)
    
    # Calcula média por UF
    medias_uf = []
    for uf, valores in valores_por_uf.items():
        media = sum(valores) / len(valores)
        medias_uf.append({'uf': uf, 'media': media})
    
    # Ordena por média
    medias_uf.sort(key=lambda x: x['media'], reverse=True)
    
    labels = [item['uf'] for item in medias_uf]
    values = [item['media'] for item in medias_uf]
    
    return {
        'labels': labels,
        'values': values
    }


def get_valor_condenacao_por_uf():
    """
    Retorna valor médio de condenação por UF (todos).
    """
    valores_por_uf = {}
    
    for p in Processo.objects.exclude(valor_condenacao__isnull=True).exclude(valor_condenacao=''):
        if p.uf:
            valor = parse_valor_monetario(p.valor_condenacao)
            if valor > 0:
                if p.uf not in valores_por_uf:
                    valores_por_uf[p.uf] = []
                valores_por_uf[p.uf].append(valor)
    
    # Calcula média por UF
    medias_uf = []
    for uf, valores in valores_por_uf.items():
        media = sum(valores) / len(valores)
        medias_uf.append({'uf': uf, 'media': media})
    
    # Ordena por média
    medias_uf.sort(key=lambda x: x['media'], reverse=True)
    
    labels = [item['uf'] for item in medias_uf]
    values = [item['media'] for item in medias_uf]
    
    return {
        'labels': labels,
        'values': values
    }


def calcular_duracao_processo(data_dist, data_fim):
    """
    Calcula duração em dias entre duas datas.
    """
    if not data_dist or not data_fim:
        return None
    
    data_inicio = parse_data_brasileira(data_dist)
    data_final = parse_data_brasileira(data_fim)
    
    if data_inicio and data_final:
        return (data_final - data_inicio).days
    
    return None


def get_duracao_media_por_uf():
    """
    Retorna duração média de processos por UF.
    Compara 3 métricas: até arquivamento, até sentença, até acórdão.
    """
    duracoes_arquivamento = {}
    duracoes_sentenca = {}
    duracoes_acordao = {}
    
    for p in Processo.objects.all():
        if not p.uf or not p.data_distribuicao:
            continue
        
        # Duração até arquivamento
        if p.data_arquivamento:
            duracao = calcular_duracao_processo(p.data_distribuicao, p.data_arquivamento)
            if duracao and duracao > 0:
                if p.uf not in duracoes_arquivamento:
                    duracoes_arquivamento[p.uf] = []
                duracoes_arquivamento[p.uf].append(duracao)
        
        # Duração até sentença
        if p.data_sentenca:
            duracao = calcular_duracao_processo(p.data_distribuicao, p.data_sentenca)
            if duracao and duracao > 0:
                if p.uf not in duracoes_sentenca:
                    duracoes_sentenca[p.uf] = []
                duracoes_sentenca[p.uf].append(duracao)
        
        # Duração até acórdão
        if p.data_primeiro_acordao:
            duracao = calcular_duracao_processo(p.data_distribuicao, p.data_primeiro_acordao)
            if duracao and duracao > 0:
                if p.uf not in duracoes_acordao:
                    duracoes_acordao[p.uf] = []
                duracoes_acordao[p.uf].append(duracao)
    
    # Pegar todas as UFs que têm pelo menos uma métrica
    todas_ufs = set(list(duracoes_arquivamento.keys()) + list(duracoes_sentenca.keys()) + list(duracoes_acordao.keys()))
    
    # Calcular médias
    medias_ufs = []
    for uf in todas_ufs:
        media_arq = sum(duracoes_arquivamento.get(uf, [])) / len(duracoes_arquivamento.get(uf, [1])) if uf in duracoes_arquivamento else 0
        media_sent = sum(duracoes_sentenca.get(uf, [])) / len(duracoes_sentenca.get(uf, [1])) if uf in duracoes_sentenca else 0
        media_acor = sum(duracoes_acordao.get(uf, [])) / len(duracoes_acordao.get(uf, [1])) if uf in duracoes_acordao else 0
        
        # Ordenar pela média geral
        media_geral = (media_arq + media_sent + media_acor) / 3 if (media_arq + media_sent + media_acor) > 0 else 0
        
        medias_ufs.append({
            'uf': uf,
            'media_geral': media_geral,
            'arquivamento': media_arq,
            'sentenca': media_sent,
            'acordao': media_acor
        })
    
    # Ordenar e pegar top 10
    medias_ufs.sort(key=lambda x: x['media_geral'], reverse=True)
    medias_ufs = medias_ufs[:10]
    
    labels = [item['uf'] for item in medias_ufs]
    arquivamento = [item['arquivamento'] for item in medias_ufs]
    sentenca = [item['sentenca'] for item in medias_ufs]
    acordao = [item['acordao'] for item in medias_ufs]
    
    return {
        'labels': labels,
        'arquivamento': arquivamento,
        'sentenca': sentenca,
        'acordao': acordao
    }


def get_processos_por_fase():
    """
    Retorna quantidade de processos por fase.
    """
    processos_fase = Processo.objects.values('fase').annotate(
        total=Count('numero_processo')
    ).order_by('-total')
    
    labels = []
    values = []
    
    for item in processos_fase:
        if item['fase']:
            labels.append(item['fase'])
            values.append(item['total'])
    
    return {
        'labels': labels,
        'values': values
    }


# ===========================
# FUNÇÕES PARA MÓDULO DISTRIBUIÇÃO
# ===========================

def get_volume_distribuicao():
    """
    Retorna volume de processos distribuídos por ano.
    """
    from collections import defaultdict
    
    processos_por_ano = defaultdict(int)
    
    for p in Processo.objects.exclude(data_distribuicao__isnull=True).exclude(data_distribuicao=''):
        data = parse_data_brasileira(p.data_distribuicao)
        if data:
            ano = data.year
            processos_por_ano[ano] += 1
    
    # Ordenar por ano
    anos_ordenados = sorted(processos_por_ano.keys())
    
    labels = [str(ano) for ano in anos_ordenados]
    values = [processos_por_ano[ano] for ano in anos_ordenados]
    
    return {
        'labels': labels,
        'values': values
    }


def get_ranking_distribuicao(criterio='comarca'):
    """
    Retorna ranking de distribuição de processos por critério.
    Critérios: comarca, classe, assuntos, magistrado, origem, atividade_economica, tribunal, advogado_polo_ativo, cargo
    """
    from collections import defaultdict
    
    # Mapear critério para campo do modelo
    campo_map = {
        'comarca': 'comarca',
        'classe': 'classe',
        'assuntos': 'assuntos',
        'magistrado': 'magistrado',
        'origem': 'orgao_origem',
        'atividade_economica': 'atividade_economica',
        'tribunal': 'tribunal',
        'advogado_polo_ativo': 'advogado_polo_ativo',
        'cargo': 'cargo'
    }
    
    campo = campo_map.get(criterio, 'comarca')
    
    # Contar processos por critério
    contagem = defaultdict(int)
    
    for p in Processo.objects.all():
        valor = getattr(p, campo, None)
        if valor and valor.strip():
            # Para assuntos, pode ter múltiplos separados por vírgula
            if campo == 'assuntos' and ',' in valor:
                assuntos_list = [a.strip() for a in valor.split(',')]
                for assunto in assuntos_list:
                    if assunto:
                        contagem[assunto] += 1
            else:
                contagem[valor.strip()] += 1
    
    # Ordenar por quantidade (decrescente) e pegar top 20
    ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:20]
    
    labels = [item[0] for item in ranking]
    values = [item[1] for item in ranking]
    
    return {
        'labels': labels,
        'values': values
    }
