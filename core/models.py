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
    valor_custas = models.CharField(max_length=50, null=True, blank=True, verbose_name="Valor de Custas (R$)")
    valor_diferenca_custas = models.CharField(max_length=50, null=True, blank=True, verbose_name="Valor de Diferença de Custas (R$)")

    # Campos adicionais presentes na planilha-base (enriquecimento)
    justica_gratuita = models.CharField(max_length=10, null=True, blank=True, verbose_name="Justiça Gratuita?")
    segredo_justica = models.CharField(max_length=10, null=True, blank=True, verbose_name="Segredo de Justiça?")
    deve_reembolso = models.CharField(max_length=10, null=True, blank=True, verbose_name="Deve Reembolso?")
    possui_pedido_substituicao = models.CharField(max_length=10, null=True, blank=True, verbose_name="Possui Pedido de Substituição")
    ultimo_salario = models.CharField(max_length=50, null=True, blank=True, verbose_name="Último Salário")
    data_admissao_demissao = models.CharField(max_length=60, null=True, blank=True, verbose_name="Data de Admissão / Demissão")
    ultimo_movimento = models.TextField(null=True, blank=True, verbose_name="Último Movimento")
    data_ultimo_movimento = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data do Último Movimento")
    pagamentos_recursos = models.TextField(null=True, blank=True, verbose_name="Pagamentos de Recursos")
    tipo_pedido_valor_desfecho = models.TextField(null=True, blank=True, verbose_name="TipoPedido / Valor / Desfecho")

    # Integração ControlJus / controle de sincronização
    controljus_id = models.BigIntegerField(null=True, blank=True, unique=True, db_index=True, verbose_name="ID ControlJus")
    cnj_normalizado = models.CharField(max_length=25, null=True, blank=True, db_index=True, verbose_name="CNJ (somente dígitos)")
    origem = models.CharField(max_length=20, default="planilha", verbose_name="Origem do registro")
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True, verbose_name="Última Sincronização")
    ultima_analise_ia = models.DateTimeField(null=True, blank=True, verbose_name="Última Análise IA")

    class Meta:
        managed = True
        db_table = "processos"
        verbose_name = "Processo"
        verbose_name_plural = "Processos"

    def __str__(self):
        return self.numero_processo


class PedidoCatalogo(models.Model):
    """
    Catálogo padronizado de tipos de pedido (dicionário canônico).

    Semeado a partir dos 288 tipos usados na planilha-base. A análise por IA
    SEMPRE normaliza pedidos contra este catálogo para evitar que o mesmo
    pedido apareça com nomes diferentes. ``aliases`` guarda grafias
    alternativas conhecidas (JSON list).
    """

    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome canônico")
    aliases = models.JSONField(default=list, blank=True, verbose_name="Grafias alternativas")
    ocorrencias_base = models.IntegerField(default=0, verbose_name="Ocorrências na planilha-base")
    ativo = models.BooleanField(default=True)
    criado_por_ia = models.BooleanField(default=False, verbose_name="Sugerido pela IA")

    class Meta:
        db_table = "pedidos_catalogo"
        verbose_name = "Pedido (catálogo)"
        verbose_name_plural = "Pedidos (catálogo)"

    def __str__(self):
        return self.nome


class PedidoProcesso(models.Model):
    """
    Pedido individual de um processo, normalizado contra o catálogo.
    Fonte da verdade para os módulos de Pedidos/Valores; a coluna legada
    ``Processo.pedidos`` é materializada a partir daqui.
    """

    RESULTADOS = [
        ("PLEITEADO", "Pleiteado"),
        ("DEFERIMENTO", "Deferimento"),
        ("INDEFERIMENTO", "Indeferimento"),
        ("DEFERIMENTO PARCIAL", "Deferimento Parcial"),
        ("INDETERMINADO", "Indeterminado"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="pedidos_norm")
    catalogo = models.ForeignKey(PedidoCatalogo, on_delete=models.PROTECT, related_name="usos")
    nome_original = models.CharField(max_length=255, blank=True, default="", verbose_name="Nome como apareceu na fonte")
    valor_pleiteado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    resultado = models.CharField(max_length=25, choices=RESULTADOS, default="PLEITEADO")
    instancia = models.IntegerField(null=True, blank=True, verbose_name="Instância da decisão")
    fundamentacao = models.TextField(blank=True, default="", verbose_name="Fundamentação resumida")
    confianca_ia = models.FloatField(null=True, blank=True, verbose_name="Confiança da IA (0-1)")
    fonte = models.CharField(max_length=30, default="planilha", verbose_name="Fonte (planilha/ia/manual)")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pedidos_processo"
        unique_together = [("processo", "catalogo")]
        verbose_name = "Pedido do Processo"
        verbose_name_plural = "Pedidos dos Processos"

    def __str__(self):
        return f"{self.processo_id} · {self.catalogo.nome} · {self.resultado}"


class Movimentacao(models.Model):
    """
    Movimentação (andamento) bruta importada do ControlJus.
    ``andamento_id`` é o ID único no ControlJus — chave de idempotência
    da sincronização incremental. O texto do recorte (DJEN) fica aqui.
    """

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="movimentacoes")
    andamento_id = models.BigIntegerField(unique=True, db_index=True)
    data_hora = models.DateTimeField(null=True, blank=True, db_index=True)
    nome = models.TextField(blank=True, default="")
    tipo_andamento = models.CharField(max_length=100, blank=True, default="")
    descricao_fonte = models.CharField(max_length=150, blank=True, default="")
    recorte_texto = models.TextField(blank=True, default="", verbose_name="Texto do recorte (DJEN)")
    recorte_diario = models.CharField(max_length=150, blank=True, default="")
    recorte_disponibilizacao = models.DateTimeField(null=True, blank=True)
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movimentacoes"
        indexes = [models.Index(fields=["processo", "data_hora"])]
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"

    def __str__(self):
        return f"{self.processo_id} · {str(self.data_hora)[:10]} · {self.nome[:40]}"


class Decisao(models.Model):
    """
    Ato decisório identificado nas movimentações (sentença, acórdão,
    decisão, homologação de acordo...). Quando há texto (recorte DJEN),
    a IA analisa e grava o resultado estruturado em ``analise_json``.
    """

    TIPOS = [
        ("sentenca", "Sentença"),
        ("acordao", "Acórdão"),
        ("decisao", "Decisão"),
        ("despacho", "Despacho"),
        ("homologacao_acordo", "Homologação de Acordo"),
        ("embargos", "Embargos de Declaração"),
        ("transito", "Trânsito em Julgado"),
        ("arquivamento", "Arquivamento"),
    ]
    STATUS_ANALISE = [
        ("pendente", "Pendente"),
        ("analisado", "Analisado"),
        ("sem_texto", "Sem texto disponível"),
        ("erro", "Erro"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="decisoes")
    movimentacao = models.ForeignKey(Movimentacao, on_delete=models.SET_NULL, null=True, blank=True, related_name="decisoes")
    tipo_ato = models.CharField(max_length=30, choices=TIPOS)
    data = models.DateTimeField(null=True, blank=True, db_index=True)
    grau = models.IntegerField(null=True, blank=True, verbose_name="Grau/Instância")
    texto = models.TextField(blank=True, default="", verbose_name="Íntegra disponível")
    fonte_texto = models.CharField(max_length=30, blank=True, default="", verbose_name="Fonte do texto")
    resultado = models.CharField(max_length=120, blank=True, default="", verbose_name="Resultado inferido")
    analise_json = models.JSONField(null=True, blank=True, verbose_name="Análise estruturada da IA")
    status_analise = models.CharField(max_length=15, choices=STATUS_ANALISE, default="pendente")
    modelo_ia = models.CharField(max_length=60, blank=True, default="")
    data_analise = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "decisoes"
        indexes = [models.Index(fields=["processo", "tipo_ato"])]
        verbose_name = "Decisão"
        verbose_name_plural = "Decisões"

    def __str__(self):
        return f"{self.processo_id} · {self.tipo_ato} · {str(self.data)[:10]}"


class SincronizacaoLog(models.Model):
    """Registro de execuções de sincronização/análise (auditoria do cron)."""

    comando = models.CharField(max_length=60)
    inicio = models.DateTimeField(auto_now_add=True)
    fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="executando")
    detalhes = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "sincronizacao_logs"
        ordering = ["-inicio"]
        verbose_name = "Log de Sincronização"
        verbose_name_plural = "Logs de Sincronização"

    def __str__(self):
        return f"{self.comando} · {self.inicio:%d/%m/%Y %H:%M} · {self.status}"
