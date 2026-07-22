"""
Materialização das colunas legadas do Processo a partir das tabelas
normalizadas (PedidoProcesso, Decisao, Movimentacao).

As telas e gráficos existentes leem as colunas de texto do Processo
(``pedidos``, ``decisoes_por_instancia``, ``tipos_recursos``...). As
tabelas normalizadas são a fonte da verdade; esta camada mantém as
colunas legadas coerentes sem exigir refatoração dos gráficos.
"""

from core.services import extracao


def materializar_processo(processo):
    """Recalcula colunas derivadas de um processo. Retorna campos alterados."""
    alterados = []

    # ---- Pedidos (lista canônica, ordenada) + TipoPedido/Valor/Desfecho
    pedidos = list(
        processo.pedidos_norm.select_related("catalogo").order_by("catalogo__nome")
    )
    if pedidos:
        texto_pedidos = ", ".join(p.catalogo.nome for p in pedidos)
        if processo.pedidos != texto_pedidos:
            processo.pedidos = texto_pedidos
            alterados.append("pedidos")

        partes = []
        for p in pedidos:
            valor = (
                f"R$ {p.valor_pleiteado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if p.valor_pleiteado is not None
                else "R$ 0,00"
            )
            partes.append(f"{p.catalogo.nome} / {valor} / {p.resultado}")
        texto_tvd = ", ".join(partes)
        if processo.tipo_pedido_valor_desfecho != texto_tvd:
            processo.tipo_pedido_valor_desfecho = texto_tvd
            alterados.append("tipo_pedido_valor_desfecho")

    # ---- Decisões por instância ("Grau 1 - X, Grau 2 - Y")
    decisoes = list(
        processo.decisoes.filter(resultado__gt="").order_by("grau", "data")
    )
    if decisoes:
        por_grau = {}
        for d in decisoes:
            grau = d.grau or 1
            rotulos = por_grau.setdefault(grau, [])
            if d.resultado not in rotulos:
                rotulos.append(d.resultado)
        texto_dpi = ", ".join(
            f"Grau {g} - " + ", ".join(rotulos) for g, rotulos in sorted(por_grau.items())
        )
        if processo.decisoes_por_instancia != texto_dpi:
            processo.decisoes_por_instancia = texto_dpi
            alterados.append("decisoes_por_instancia")

    # ---- Tipos de recursos e indicativos, a partir das movimentações brutas
    nomes_movs = list(processo.movimentacoes.values_list("nome", flat=True))
    if nomes_movs:
        recursos = extracao.detectar_recursos(nomes_movs)
        if recursos:
            texto_rec = ", ".join(recursos)
            if processo.tipos_recursos != texto_rec:
                processo.tipos_recursos = texto_rec
                alterados.append("tipos_recursos")

        bloqueio = "Sim" if extracao.detectar_bloqueio(nomes_movs) else "Não"
        if (processo.indicativo_bloqueio or "Não") != bloqueio and bloqueio == "Sim":
            processo.indicativo_bloqueio = bloqueio
            alterados.append("indicativo_bloqueio")

        revelia = "Sim" if extracao.detectar_revelia(nomes_movs) else "Não"
        if (processo.indicativo_revelia or "Não") != revelia and revelia == "Sim":
            processo.indicativo_revelia = revelia
            alterados.append("indicativo_revelia")

    if alterados:
        processo.save(update_fields=alterados)
    return alterados
