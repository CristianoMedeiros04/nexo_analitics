"""
Oráculo — assistente de IA com acesso ao banco de jurimetria.

Arquitetura (tool use):
1. monta um RETRATO abrangente do dataset (snapshot) no system prompt,
   dando à IA grounding imediato para a maioria das perguntas;
2. expõe FERRAMENTAS de consulta estruturada (executadas via ORM, sem SQL
   cru) para a IA obter números exatos e drilar em qualquer dimensão;
3. roda um loop de tool use com o DeepSeek (OpenAI-compatível), deixando a
   IA consultar → raciocinar → concluir.

Provedor: DEEPSEEK_API_KEY (padrão) ou ANTHROPIC_API_KEY (fallback simples,
sem tools — responde só com o snapshot).
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

from django.db.models import Count

from core.models import Decisao, Movimentacao, PedidoProcesso, Processo, SincronizacaoLog

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODELO_DEEPSEEK = "deepseek-chat"

# ------------------------------------------------------------------ helpers
def _parse_valor(texto):
    if texto in (None, ""):
        return None
    try:
        return float(str(texto).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def _ano(texto):
    if not texto:
        return None
    m = re.search(r"(\d{4})", str(texto))
    return m.group(1) if m else None


def _reais(v):
    if v is None:
        return "—"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _multi(texto):
    """Divide campo-lista (vírgula/;) em nomes limpos."""
    if not texto:
        return []
    return [n.strip() for n in str(texto).replace(";", ",").split(",") if len(n.strip()) > 2]


# ----------------------------------------------------------------- snapshot
def construir_snapshot():
    """Retrato agregado do dataset para o system prompt."""
    qs = Processo.objects.all()
    total = qs.count()
    linhas = [f"Total de processos monitorados: {total}."]

    def topo(campo, rotulo, n=10):
        c = Counter()
        for v in qs.values_list(campo, flat=True):
            if v not in (None, ""):
                c[v] += 1
        if c:
            itens = ", ".join(f"{k}: {v}" for k, v in c.most_common(n))
            linhas.append(f"{rotulo} (top {n}): {itens}.")

    def topo_multi(campo, rotulo, n=8):
        c = Counter()
        for v in qs.values_list(campo, flat=True):
            for nome in _multi(v):
                c[nome] += 1
        if c:
            linhas.append(f"{rotulo} (top {n}): " + ", ".join(f"{k}: {v}" for k, v in c.most_common(n)) + ".")

    topo("situacao", "Por situação", 5)
    topo("fase", "Por fase", 5)
    topo("instancia", "Por instância", 5)
    topo("uf", "Por UF", 12)
    topo("tribunal", "Por tribunal", 12)
    topo("comarca", "Por comarca", 10)
    topo("classe", "Por classe processual", 8)
    topo("desfecho", "Por desfecho", 15)
    topo_multi("assuntos", "Assuntos mais comuns")
    topo_multi("juizes", "Magistrados mais frequentes")

    # datas
    anos = Counter()
    for v in qs.values_list("data_distribuicao", flat=True):
        a = _ano(v)
        if a:
            anos[a] += 1
    if anos:
        linhas.append("Distribuição por ano: " + ", ".join(f"{a}: {n}" for a, n in sorted(anos.items())) + ".")

    # valores
    for campo, rot in [("valor_causa", "causa"), ("valor_condenacao", "condenação"), ("valor_acordo", "acordo")]:
        vals = [x for x in (_parse_valor(v) for v in qs.values_list(campo, flat=True)) if x]
        if vals:
            linhas.append(f"Valor de {rot}: {len(vals)} processos, soma {_reais(sum(vals))}, média {_reais(sum(vals)/len(vals))}.")

    # pedidos (IA + planilha)
    res = Counter()
    for r in PedidoProcesso.objects.values_list("resultado", flat=True):
        res[r] += 1
    if res:
        linhas.append("Resultados de pedidos: " + ", ".join(f"{k}: {v}" for k, v in res.most_common()) + ".")
    # top pedidos com taxa
    agg = defaultdict(lambda: {"d": 0, "p": 0, "i": 0, "t": 0})
    for nome, r in PedidoProcesso.objects.values_list("catalogo__nome", "resultado"):
        a = agg[nome]; a["t"] += 1
        if r == "DEFERIMENTO": a["d"] += 1
        elif r == "DEFERIMENTO PARCIAL": a["p"] += 1
        elif r == "INDEFERIMENTO": a["i"] += 1
    ped_top = sorted(agg.items(), key=lambda kv: -kv[1]["t"])[:12]
    if ped_top:
        parts = []
        for nome, a in ped_top:
            jul = a["d"] + a["p"] + a["i"]
            taxa = f"{100*(a['d']+0.5*a['p'])/jul:.0f}%" if jul else "s/ julgados"
            parts.append(f"{nome} (vol {a['t']}, deferimento {taxa})")
        linhas.append("Pedidos mais frequentes: " + "; ".join(parts) + ".")

    # decisões / movimentações
    dec = Decisao.objects.count()
    dec_ia = Decisao.objects.filter(status_analise="analisado").count()
    mov = Movimentacao.objects.count()
    linhas.append(f"Base processual: {mov} movimentações, {dec} atos decisórios ({dec_ia} analisados pela IA).")

    # sync
    ult = SincronizacaoLog.objects.filter(comando__in=["cj_sincronizar", "sync_semanal"]).order_by("-inicio").first()
    if ult:
        linhas.append(f"Última sincronização com o ControlJus: {ult.inicio:%d/%m/%Y %H:%M} ({ult.status}).")

    return "\n".join(linhas)


# --------------------------------------------------- executor de consultas
_DIM_DIRETA = {  # dimensão -> campo do model
    "uf": "uf", "tribunal": "tribunal", "comarca": "comarca", "classe": "classe",
    "fase": "fase", "situacao": "situacao", "desfecho": "desfecho", "instancia": "instancia",
    "vara": "vara",
}
_DIM_MULTI = {"magistrado": "juizes", "advogado": "advogados_polo_ativo", "assunto": "assuntos"}


def _base_qs(filtros):
    from api.views import aplicar_filtros  # reuso do motor de filtros
    return aplicar_filtros(Processo.objects.all(), filtros or {})


def executar_consulta(spec):
    """Executa uma consulta estruturada. Retorna dict serializável."""
    fonte = spec.get("fonte", "processos")
    metrica = spec.get("metrica", "contagem")
    dim = spec.get("agrupar_por")
    filtros = spec.get("filtros") or {}
    ordenar = spec.get("ordenar", "desc")
    limite = min(int(spec.get("limite", 15) or 15), 50)
    campo_valor = spec.get("campo_valor", "valor_causa")

    # roteamento: taxa de deferimento por dimensão de PROCESSO (tribunal, uf,
    # comarca, magistrado, advogado...) é sempre calculada na fonte processos,
    # que pondera os pedidos dos processos de cada grupo. Só "pedido" fica na
    # fonte pedidos. Assim a IA obtém o ranking direto, sem recalcular à mão.
    if metrica == "taxa_deferimento" and (dim in _DIM_DIRETA or dim in _DIM_MULTI):
        fonte = "processos"

    qs = _base_qs(filtros)

    # ---------- fonte pedidos ----------
    if fonte == "pedidos":
        pp = PedidoProcesso.objects.filter(processo__in=qs)
        if metrica == "taxa_deferimento" and dim not in ("pedido",):
            # taxa global sobre todos os pedidos julgados
            g = {"d": 0, "p": 0, "i": 0, "t": 0}
            for r in pp.values_list("resultado", flat=True):
                g["t"] += 1
                if r == "DEFERIMENTO": g["d"] += 1
                elif r == "DEFERIMENTO PARCIAL": g["p"] += 1
                elif r == "INDEFERIMENTO": g["i"] += 1
            jul = g["d"] + g["p"] + g["i"]
            return {"tipo": "escalar", "metrica": "taxa_deferimento",
                    "taxa_deferimento": round(100*(g["d"]+0.5*g["p"])/jul, 1) if jul else None,
                    "deferimentos": g["d"], "parciais": g["p"], "indeferimentos": g["i"],
                    "julgados": jul, "total_pedidos": g["t"]}
        if dim in ("pedido", "resultado_pedido"):
            campo = "catalogo__nome" if dim == "pedido" else "resultado"
            if metrica == "taxa_deferimento" and dim == "pedido":
                agg = defaultdict(lambda: {"d": 0, "p": 0, "i": 0, "t": 0})
                for nome, r in pp.values_list("catalogo__nome", "resultado"):
                    a = agg[nome]; a["t"] += 1
                    if r == "DEFERIMENTO": a["d"] += 1
                    elif r == "DEFERIMENTO PARCIAL": a["p"] += 1
                    elif r == "INDEFERIMENTO": a["i"] += 1
                linhas = []
                for nome, a in agg.items():
                    jul = a["d"] + a["p"] + a["i"]
                    if jul < 3:
                        continue
                    linhas.append({"grupo": nome, "julgados": jul, "volume": a["t"],
                                   "taxa_deferimento": round(100*(a["d"]+0.5*a["p"])/jul, 1)})
                linhas.sort(key=lambda x: -x["taxa_deferimento"], reverse=(ordenar == "asc"))
                return {"tipo": "ranking", "metrica": "taxa_deferimento", "resultado": linhas[:limite]}
            dados = list(pp.values(campo).annotate(n=Count("id")).order_by(("-" if ordenar == "desc" else "") + "n")[:limite])
            return {"tipo": "agregado", "resultado": [{"grupo": d[campo], "valor": d["n"]} for d in dados]}
        return {"tipo": "escalar", "metrica": "contagem_pedidos", "valor": pp.count()}

    # ---------- fonte decisoes ----------
    if fonte == "decisoes":
        dqs = Decisao.objects.filter(processo__in=qs)
        if dim in ("tipo_ato", "status_analise", "grau"):
            dados = list(dqs.values(dim).annotate(n=Count("id")).order_by("-n")[:limite])
            return {"tipo": "agregado", "resultado": [{"grupo": d[dim], "valor": d["n"]} for d in dados]}
        return {"tipo": "escalar", "metrica": "contagem_decisoes", "valor": dqs.count()}

    # ---------- fonte processos ----------
    if metrica in ("soma_valor", "media_valor"):
        # agrupado ou global
        if dim in _DIM_DIRETA:
            campo = _DIM_DIRETA[dim]
            grupos = defaultdict(list)
            for g, v in qs.values_list(campo, campo_valor):
                fv = _parse_valor(v)
                if fv is not None and g:
                    grupos[g].append(fv)
            linhas = []
            for g, vs in grupos.items():
                total = sum(vs)
                linhas.append({"grupo": g, "soma": round(total, 2), "media": round(total/len(vs), 2), "n": len(vs)})
            linhas.sort(key=lambda x: x["soma" if metrica == "soma_valor" else "media"], reverse=(ordenar != "asc"))
            return {"tipo": "ranking", "metrica": metrica, "campo": campo_valor, "resultado": linhas[:limite]}
        vals = [x for x in (_parse_valor(v) for v in qs.values_list(campo_valor, flat=True)) if x is not None]
        if not vals:
            return {"tipo": "escalar", "valor": 0, "n": 0}
        return {"tipo": "escalar", "campo": campo_valor,
                "soma": round(sum(vals), 2), "media": round(sum(vals)/len(vals), 2), "n": len(vals)}

    if metrica == "taxa_deferimento":
        # taxa por dimensão (magistrado/advogado/uf/tribunal...) usando pedidos dos processos
        por_proc = defaultdict(lambda: {"d": 0, "p": 0, "i": 0})
        for pid, r in PedidoProcesso.objects.filter(processo__in=qs).values_list("processo_id", "resultado"):
            t = por_proc[pid]
            if r == "DEFERIMENTO": t["d"] += 1
            elif r == "DEFERIMENTO PARCIAL": t["p"] += 1
            elif r == "INDEFERIMENTO": t["i"] += 1
        agg = defaultdict(lambda: {"d": 0, "p": 0, "i": 0, "proc": 0})
        campo = _DIM_DIRETA.get(dim) or _DIM_MULTI.get(dim)
        if not campo:
            # taxa global
            g = {"d": 0, "p": 0, "i": 0}
            for t in por_proc.values():
                for k in g: g[k] += t[k]
            jul = g["d"] + g["p"] + g["i"]
            return {"tipo": "escalar", "metrica": "taxa_deferimento",
                    "taxa": round(100*(g["d"]+0.5*g["p"])/jul, 1) if jul else None, "julgados": jul}
        for pid, texto in qs.values_list("numero_processo", campo):
            nomes = _multi(texto) if dim in _DIM_MULTI else ([texto] if texto else [])
            t = por_proc.get(pid)
            for nome in nomes:
                a = agg[nome]; a["proc"] += 1
                if t:
                    a["d"] += t["d"]; a["p"] += t["p"]; a["i"] += t["i"]
        linhas = []
        for nome, a in agg.items():
            jul = a["d"] + a["p"] + a["i"]
            if jul < 5:
                continue
            linhas.append({"grupo": nome, "processos": a["proc"], "julgados": jul,
                           "taxa_deferimento": round(100*(a["d"]+0.5*a["p"])/jul, 1)})
        linhas.sort(key=lambda x: x["taxa_deferimento"], reverse=(ordenar != "asc"))
        return {"tipo": "ranking", "metrica": "taxa_deferimento", "resultado": linhas[:limite]}

    # metrica contagem
    if dim in _DIM_DIRETA:
        campo = _DIM_DIRETA[dim]
        dados = list(qs.exclude(**{f"{campo}__isnull": True}).values(campo).annotate(n=Count("numero_processo"))
                     .order_by(("-" if ordenar == "desc" else "") + "n")[:limite + 1])
        limpos = [{"grupo": d[campo], "valor": d["n"]} for d in dados if d[campo] not in (None, "")]
        return {"tipo": "agregado", "dimensao": dim, "resultado": limpos[:limite]}
    if dim in _DIM_MULTI:
        c = Counter()
        for v in qs.values_list(_DIM_MULTI[dim], flat=True):
            for nome in _multi(v):
                c[nome] += 1
        itens = c.most_common(limite) if ordenar == "desc" else sorted(c.items(), key=lambda x: x[1])[:limite]
        return {"tipo": "agregado", "dimensao": dim, "resultado": [{"grupo": k, "valor": v} for k, v in itens]}
    if dim == "ano_distribuicao":
        c = Counter()
        for v in qs.values_list("data_distribuicao", flat=True):
            a = _ano(v)
            if a: c[a] += 1
        return {"tipo": "serie", "dimensao": "ano", "resultado": [{"grupo": a, "valor": n} for a, n in sorted(c.items())]}
    return {"tipo": "escalar", "metrica": "contagem", "valor": qs.count()}


def buscar_processo(cnj):
    """Detalhe de um processo por CNJ (com/sem máscara)."""
    norm = re.sub(r"\D", "", cnj or "")
    p = (Processo.objects.filter(cnj_normalizado=norm).first()
         or Processo.objects.filter(numero_processo=cnj).first())
    if not p:
        return {"encontrado": False}
    peds = list(p.pedidos_norm.select_related("catalogo").values("catalogo__nome", "resultado", "valor_pleiteado")[:60])
    return {
        "encontrado": True, "cnj": p.numero_processo,
        "uf": p.uf, "comarca": p.comarca, "tribunal": p.tribunal, "vara": p.vara,
        "classe": p.classe, "assuntos": p.assuntos, "fase": p.fase, "situacao": p.situacao,
        "instancia": p.instancia, "desfecho": p.desfecho, "juizes": p.juizes,
        "partes_ativo": p.partes_polo_ativo, "partes_passivo": p.partes_polo_passivo,
        "advogados_ativo": p.advogados_polo_ativo,
        "valor_causa": p.valor_causa, "valor_condenacao": p.valor_condenacao, "valor_acordo": p.valor_acordo,
        "data_distribuicao": p.data_distribuicao, "data_sentenca": p.data_sentenca,
        "data_transito_julgado": p.data_transito_julgado,
        "pedidos": [{"pedido": x["catalogo__nome"], "resultado": x["resultado"],
                     "valor": float(x["valor_pleiteado"]) if x["valor_pleiteado"] else None} for x in peds],
    }


# --------------------------------------------------------------- ferramentas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_banco",
            "description": ("Consulta agregada ao banco de processos trabalhistas. Use SEMPRE que precisar "
                            "de números exatos, rankings, distribuições ou taxas. Retorna JSON."),
            "parameters": {
                "type": "object",
                "properties": {
                    "fonte": {"type": "string", "enum": ["processos", "pedidos", "decisoes"],
                              "description": "processos (padrão), pedidos (resultados/taxas) ou decisoes."},
                    "metrica": {"type": "string",
                                "enum": ["contagem", "taxa_deferimento", "soma_valor", "media_valor"],
                                "description": "contagem; taxa_deferimento (deferido+0.5*parcial sobre julgados); soma/media de valor."},
                    "agrupar_por": {"type": "string",
                                    "description": "dimensão opcional: uf, tribunal, comarca, classe, fase, situacao, "
                                                   "desfecho, instancia, vara, ano_distribuicao, magistrado, advogado, "
                                                   "assunto, pedido, resultado_pedido, tipo_ato, status_analise."},
                    "campo_valor": {"type": "string", "enum": ["valor_causa", "valor_condenacao", "valor_acordo"],
                                    "description": "para soma_valor/media_valor."},
                    "filtros": {"type": "object",
                                "description": "filtros (listas): ufs, tribunais, comarcas, classes, fase, status, "
                                               "desfecho, assuntos, magistrados, advogados, tipos_pedido, jurisdicao."},
                    "ordenar": {"type": "string", "enum": ["desc", "asc"]},
                    "limite": {"type": "integer", "description": "máx. de grupos (padrão 15, teto 50)."},
                },
                "required": ["fonte", "metrica"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detalhar_processo",
            "description": "Retorna os detalhes completos de um processo específico a partir do número CNJ.",
            "parameters": {
                "type": "object",
                "properties": {"cnj": {"type": "string", "description": "Número do processo (CNJ)."}},
                "required": ["cnj"],
            },
        },
    },
]


def _dispatch(nome, args):
    try:
        if nome == "consultar_banco":
            return executar_consulta(args)
        if nome == "detalhar_processo":
            return buscar_processo(args.get("cnj", ""))
        return {"erro": f"ferramenta desconhecida: {nome}"}
    except Exception as exc:  # nunca quebra o loop
        return {"erro": str(exc)[:300]}


SYSTEM = """Você é o Oráculo do Nexo Analitics — um analista de jurimetria trabalhista sênior com acesso ao banco de dados de processos do escritório (contrato monitorado no ControlJus).

Seu papel:
- Responder QUALQUER pergunta sobre os dados com precisão, usando as ferramentas para obter números exatos. Nunca invente números; se precisar de um dado, consulte.
- Não apenas informar: RACIOCINAR sobre os números, comparar, identificar padrões e tirar conclusões úteis para a estratégia jurídica quando fizer sentido.
- Ser objetivo e direto. Use listas e negrito quando ajudar. Formate valores em reais e percentuais de forma legível.
- Quando a pergunta for ampla ou estratégica, combine várias consultas e sintetize.
- Se um dado não existir no banco (ex.: informações não capturadas pela API), diga com franqueza em vez de supor.

Contexto atual do dataset (retrato geral — use como ponto de partida; para números exatos e recortes, consulte as ferramentas):
{snapshot}
"""


class Oraculo:
    def __init__(self):
        self.key = os.environ.get("DEEPSEEK_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key and not self.anthropic_key:
            raise RuntimeError("Nenhuma chave de IA configurada (DEEPSEEK_API_KEY/ANTHROPIC_API_KEY).")
        self.modelo = os.environ.get("IA_MODELO", MODELO_DEEPSEEK)
        if not self.modelo.startswith("deepseek"):
            self.modelo = MODELO_DEEPSEEK
        self.system = SYSTEM.replace("{snapshot}", construir_snapshot())

    def _post(self, body, tentativa=0):
        req = urllib.request.Request(
            DEEPSEEK_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and tentativa < 3:
                time.sleep(2 ** (tentativa + 1))
                return self._post(body, tentativa + 1)
            raise RuntimeError(f"DeepSeek HTTP {e.code}: {e.read().decode()[:200]}")

    def perguntar(self, pergunta, historico=None):
        """historico: lista [{role:'user'|'assistant', content:str}]. Retorna (resposta, meta)."""
        if not self.key:
            raise RuntimeError("Oráculo requer DEEPSEEK_API_KEY para tool use.")
        mensagens = [{"role": "system", "content": self.system}]
        for h in (historico or [])[-8:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                mensagens.append({"role": h["role"], "content": h["content"]})
        mensagens.append({"role": "user", "content": pergunta})

        consultas = []
        for _ in range(6):
            resp = self._post({
                "model": self.modelo, "messages": mensagens,
                "tools": TOOLS, "tool_choice": "auto", "temperature": 0.2, "max_tokens": 3000,
            })
            msg = resp["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return msg.get("content", "").strip(), {"consultas": consultas, "modelo": self.modelo}
            # registra a mensagem do assistente com as chamadas
            mensagens.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
            for tc in tool_calls:
                fn = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                resultado = _dispatch(fn, args)
                consultas.append({"ferramenta": fn, "args": args})
                mensagens.append({"role": "tool", "tool_call_id": tc["id"],
                                  "content": json.dumps(resultado, ensure_ascii=False)[:6000]})
        # excedeu rounds — pede síntese final sem tools
        resp = self._post({"model": self.modelo, "messages": mensagens, "temperature": 0.2, "max_tokens": 3000})
        return resp["choices"][0]["message"].get("content", "").strip(), {"consultas": consultas, "modelo": self.modelo}
