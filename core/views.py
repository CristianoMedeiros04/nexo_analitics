from django.shortcuts import render
from django.http import JsonResponse
from . import charts


def home(request):
    """
    View principal - Dashboard com gráficos e estatísticas.
    """
    return render(request, 'core/home.html')


def dashboard_data(request):
    """
    Retorna dados JSON para alimentar os gráficos do dashboard.
    """
    data = {
        'cards': charts.get_cards_info(),
        'processos_por_uf': charts.get_processos_por_uf(),
        'processos_por_comarca': charts.get_processos_por_comarca(),
        'valor_causa_por_uf': charts.get_valor_causa_por_uf(),
        'valor_condenacao_por_uf': charts.get_valor_condenacao_por_uf(),
        'duracao_media_por_uf': charts.get_duracao_media_por_uf(),
        'processos_por_fase': charts.get_processos_por_fase(),
    }
    
    return JsonResponse(data)


def acordos(request):
    """
    View do módulo Acordos - Dashboard com gráficos de acordos.
    """
    return render(request, 'core/acordos.html')


def desfechos(request):
    """
    View do módulo Desfechos - Dashboard com gráficos de desfechos.
    """
    return render(request, 'core/desfechos.html')


def distribuicao(request):
    """
    View do módulo Distribuição - Dashboard com gráficos de distribuição de processos.
    """
    return render(request, 'core/distribuicao.html')


def duracao(request):
    """
    View do módulo Duração - Dashboard com gráficos de duração de processos.
    """
    return render(request, 'core/duracao.html')


def revelias(request):
    """
    View do módulo Revelias - Dashboard com gráficos de revelias.
    """
    return render(request, 'core/revelias.html')



def tipos_acao(request):
    """
    View do módulo Tipos de Ação - Dashboard com gráficos de classes, assuntos e pedidos.
    """
    return render(request, 'core/tipos_acao.html')


def recursos(request):
    """
    View do módulo Recursos - Dashboard com gráficos de recursos e reversões.
    """
    return render(request, 'core/recursos.html')


def pedidos(request):
    """
    View do módulo Pedidos - Dashboard com gráficos de deferimentos e concessões.
    """
    return render(request, 'core/pedidos.html')


def valores(request):
    """
    View do módulo Valores - Dashboard com gráfico de ranking de valores.
    """
    return render(request, 'core/valores.html')


def advogados(request):
    """
    View do módulo Advogados - Comparação de métricas entre advogados.
    """
    return render(request, 'core/advogados.html')



def magistrados(request):
    """
    View do módulo Magistrados - Comparação de métricas entre magistrados.
    """
    return render(request, 'core/magistrados.html')



def oraculo(request):
    """
    Oráculo - assistente de IA conversacional com acesso ao banco de dados.
    """
    import os
    ia_disponivel = bool(os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('ANTHROPIC_API_KEY'))
    return render(request, 'core/oraculo.html', {'ia_disponivel': ia_disponivel})


def lista(request):
    """
    View do módulo Lista - Listagem de todos os processos em modo galeria.
    """
    from .models import Processo
    
    # Buscar todos os processos
    processos = Processo.objects.all().order_by('-data_distribuicao')
    
    return render(request, 'core/lista.html', {'processos': processos})
