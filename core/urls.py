from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('acordos/', views.acordos, name='acordos'),
    path('desfechos/', views.desfechos, name='desfechos'),
    path('distribuicao/', views.distribuicao, name='distribuicao'),
    path('duracao/', views.duracao, name='duracao'),
    path('revelias/', views.revelias, name='revelias'),
    path('tipos-acao/', views.tipos_acao, name='tipos_acao'),
    path('recursos/', views.recursos, name='recursos'),
    path('pedidos/', views.pedidos, name='pedidos'),
    path('valores/', views.valores, name='valores'),
    path('advogados/', views.advogados, name='advogados'),
    path('magistrados/', views.magistrados, name='magistrados'),
    path('lista/', views.lista, name='lista'),
    path('oraculo/', views.oraculo, name='oraculo'),
    path('api/dashboard-data/', views.dashboard_data, name='dashboard_data'),
]
