from django.urls import path, include
from rest_framework import routers
from .views import ProcessoViewSet, filter_options, dashboard_data_filtered, acordos_data, desfechos_data, distribuicao_data, duracao_data, revelias_data, tipos_acao_data, recursos_data, pedidos_data, valores_data, advogados_lista, advogados_desfechos, advogados_duracao, advogados_deferimento, advogados_valores_medios, advogados_valores_totais, advogados_proporcao_ativos, magistrados_lista, magistrados_desfechos, magistrados_decisoes, magistrados_duracao, magistrados_deferimento, magistrados_valores_medios, magistrados_valores_totais, magistrados_proporcao_ativos

router = routers.DefaultRouter()
router.register(r'processos', ProcessoViewSet, basename='processos')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('filter-options/', filter_options, name='filter-options'),
    path('dashboard-data-filtered/', dashboard_data_filtered, name='dashboard-data-filtered'),
    path('acordos-data/', acordos_data, name='acordos-data'),
    path('desfechos-data/', desfechos_data, name='desfechos-data'),
    path('distribuicao-data/', distribuicao_data, name='distribuicao-data'),
    path('duracao-data/', duracao_data, name='duracao-data'),
    path('revelias-data/', revelias_data, name='revelias-data'),
    path('tipos-acao-data/', tipos_acao_data, name='tipos-acao-data'),
    path('recursos-data/', recursos_data, name='recursos-data'),
    path('pedidos-data/', pedidos_data, name='pedidos-data'),
    path('valores-data/', valores_data, name='valores-data'),
    path('advogados/lista/', advogados_lista, name='advogados-lista'),
    path('advogados/desfechos/', advogados_desfechos, name='advogados-desfechos'),
    path('advogados/duracao/', advogados_duracao, name='advogados-duracao'),
    path('advogados/deferimento/', advogados_deferimento, name='advogados-deferimento'),
    path('advogados/valores-medios/', advogados_valores_medios, name='advogados-valores-medios'),
    path('advogados/valores-totais/', advogados_valores_totais, name='advogados-valores-totais'),
    path('advogados/proporcao-ativos/', advogados_proporcao_ativos, name='advogados-proporcao-ativos'),
    path('magistrados/lista/', magistrados_lista, name='magistrados-lista'),
    path('magistrados/desfechos/', magistrados_desfechos, name='magistrados-desfechos'),
    path('magistrados/decisoes/', magistrados_decisoes, name='magistrados-decisoes'),
    path('magistrados/duracao/', magistrados_duracao, name='magistrados-duracao'),
    path('magistrados/deferimento/', magistrados_deferimento, name='magistrados-deferimento'),
    path('magistrados/valores-medios/', magistrados_valores_medios, name='magistrados-valores-medios'),
    path('magistrados/valores-totais/', magistrados_valores_totais, name='magistrados-valores-totais'),
    path('magistrados/proporcao-ativos/', magistrados_proporcao_ativos, name='magistrados-proporcao-ativos'),
]
