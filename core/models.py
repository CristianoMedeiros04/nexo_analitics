from django.db import models


class Processo(models.Model):
    """
    Modelo de processo judicial (jurimetria).

    Schema gerenciado pelo Django (managed=True), com nomes de colunas
    limpos em snake_case — adequado para MySQL/produção. Os nomes de
    atributo Python são preservados para manter compatibilidade com as
    consultas do ORM em ``core/charts.py`` e ``api/views.py``.
    """

    numero_processo = models.CharField(
        max_length=50,
        primary_key=True,
        verbose_name="Número do Processo",
    )

    # Advogados
    advogados_polo_ativo = models.TextField(null=True, blank=True, verbose_name="Advogados Polo Ativo")
    advogados_polo_passivo = models.TextField(null=True, blank=True, verbose_name="Advogados Polo Passivo")

    # Classificação
    assuntos = models.TextField(null=True, blank=True, verbose_name="Assuntos")
    classe = models.TextField(null=True, blank=True, verbose_name="Classe")

    # Partes
    cnpjs = models.TextField(null=True, blank=True, verbose_name="CNPJs")
    partes_polo_ativo = models.TextField(null=True, blank=True, verbose_name="Partes Polo Ativo")
    partes_polo_passivo = models.TextField(null=True, blank=True, verbose_name="Partes Polo Passivo")
    nome_cpf = models.TextField(null=True, blank=True, verbose_name="Nome / CPF")

    # Localização
    comarca = models.CharField(max_length=100, null=True, blank=True, verbose_name="Comarca")
    uf = models.CharField(max_length=100, null=True, blank=True, verbose_name="UF")
    vara = models.TextField(null=True, blank=True, verbose_name="Vara")
    tribunal = models.TextField(null=True, blank=True, verbose_name="Tribunal")

    # Datas
    data_distribuicao = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data da Distribuição")
    data_arquivamento = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data do Arquivamento")
    data_transito_julgado = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data do Trânsito em Julgado")
    data_sentenca = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data da Sentença")
    data_primeiro_acordao = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data do Primeiro Acórdão")
    data_acordo = models.TextField(null=True, blank=True, verbose_name="Data do Acordo")

    # Status e Fase
    fase = models.CharField(max_length=50, null=True, blank=True, verbose_name="Fase")
    situacao = models.CharField(max_length=50, null=True, blank=True, verbose_name="Situação")
    instancia = models.IntegerField(null=True, blank=True, verbose_name="Instância")

    # Juízes e Magistrados
    juizes = models.TextField(null=True, blank=True, verbose_name="Juízes")
    tipo_cargos = models.TextField(null=True, blank=True, verbose_name="Tipo de Cargos")

    # Desfecho e Recursos
    desfecho = models.TextField(null=True, blank=True, verbose_name="Desfecho")
    decisoes_por_instancia = models.TextField(null=True, blank=True, verbose_name="Decisões por Instância")
    tipos_recursos = models.TextField(null=True, blank=True, verbose_name="Tipos de Recursos")
    tipo_alteracao_condenacao = models.TextField(null=True, blank=True, verbose_name="Tipo de Alteração da Condenação")
    pedidos = models.TextField(null=True, blank=True, verbose_name="Pedidos")

    # Indicativos
    indicativo_bloqueio = models.TextField(null=True, blank=True, verbose_name="Indicativo de Bloqueio")
    indicativo_revelia = models.TextField(null=True, blank=True, verbose_name="Indicativo de Revelia")

    # Valores
    valor_causa = models.CharField(max_length=50, null=True, blank=True, verbose_name="Valor de Causa (R$)")
    valor_condenacao = models.CharField(max_length=50, null=True, blank=True, verbose_name="Valor de Condenação (R$)")
    valor_acordo = models.TextField(null=True, blank=True, verbose_name="Valor de Acordo (R$)")
    valor_liquidacao = models.FloatField(null=True, blank=True, verbose_name="Valor de Liquidação (R$)")
    valor_depositos = models.TextField(null=True, blank=True, verbose_name="Valor de Depósitos (R$)")
    valor_variacao_condenacao = models.TextField(null=True, blank=True, verbose_name="Valor de Variação da Condenação (R$)")

    class Meta:
        managed = True
        db_table = "processos"
        verbose_name = "Processo"
        verbose_name_plural = "Processos"

    def __str__(self):
        return self.numero_processo
