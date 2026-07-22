"""
Extração de eventos processuais a partir dos NOMES das movimentações.

Os nomes de andamento do PJe são padronizados (Tabela Processual Unificada
do CNJ), o que permite extrair objetivamente datas e vários desfechos sem
IA — a IA entra depois, para analisar a ÍNTEGRA das decisões (recortes).
"""

import re
import unicodedata


def _norm(texto):
    """minúsculas sem acentos para matching robusto."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# (regex sobre texto normalizado, tipo_ato)
PADROES_ATO = [
    (r"\btransitad[oa] em julgado\b", "transito"),
    (r"homologada a transacao|homologacao da transacao|homologado o acordo", "homologacao_acordo"),
    (r"\bacordao\b|proferido acordao", "acordao"),
    (r"embargos de declaracao", "embargos"),
    (r"\bsentenca\b|prolatada a sentenca|julgad[oa]s? (im)?procedentes?|julgado procedente em parte|extint[oa] o processo", "sentenca"),
    (r"arquivados? os autos definitivamente|arquivamento definitivo", "arquivamento"),
    (r"\bdecisao\b|proferida decisao|concedida a tutela|indeferida a tutela|denegada a seguranca", "decisao"),
    (r"\bdespacho\b|proferido despacho", "despacho"),
]

# resultado objetivo inferível do próprio nome da movimentação
PADROES_RESULTADO = [
    (r"procedentes? em parte|parcialmente procedente", "Parcialmente Procedente"),
    (r"julgad[oa]s? improcedentes?|improcedencia", "Improcedente"),
    (r"julgad[oa]s? procedentes?", "Procedente"),
    (r"homologada a transacao|homologacao da transacao|homologado o acordo", "Acordo"),
    (r"homologada a desistencia|desistencia homologada", "Desistência"),
    (r"denegada a seguranca", "Segurança (denegação)"),
    (r"indeferida a peticao inicial", "Indeferimento da Petição Inicial"),
    (r"arquivad[oa].*ausencia do reclamante|ausencia do reclamante", "Arquivamento Ausência do Reclamante"),
    (r"sem resolucao d[eo] merito.*pressupostos|ausencia de pressupostos", "Ausência de Pressupostos Processuais"),
    (r"perempcao|litispendencia|coisa julgada", "Perempção, litispendência ou coisa julgada"),
    (r"ausencia das condicoes da acao|carencia da acao", "Ausência das Condições da Ação"),
]

# indicadores auxiliares
RE_BLOQUEIO = re.compile(r"bloqueio|sisbajud|bacenjud|penhora de valores|arresto", re.I)
RE_REVELIA = re.compile(r"\brevelia\b|\brevel\b", re.I)
RE_RECURSOS = [
    (r"recurso ordinario", "RO"),
    (r"recurso de revista", "RR"),
    (r"agravo de instrumento em recurso de revista|\bairr\b", "AIRR"),
    (r"agravo de instrumento", "AI"),
    (r"agravo de peticao", "AP"),
    (r"embargos de declaracao", "ED-PJE"),
    (r"agravo interno|agravo regimental", "AGR"),
]
RE_AUDIENCIA = re.compile(
    r"audiencia|sessao de julgamento|julgamento em pauta|pericia", re.I
)


def classificar_ato(nome_movimentacao):
    """Retorna o tipo de ato decisório do nome da movimentação, ou None."""
    n = _norm(nome_movimentacao)
    for padrao, tipo in PADROES_ATO:
        if re.search(padrao, n):
            return tipo
    return None


def inferir_resultado(nome_movimentacao):
    """Desfecho objetivo embutido no nome da movimentação, ou ''."""
    n = _norm(nome_movimentacao)
    for padrao, rotulo in PADROES_RESULTADO:
        if re.search(padrao, n):
            return rotulo
    return ""


def detectar_recursos(nomes_movimentacoes):
    """Conjunto de siglas de recursos detectadas nos nomes de movimentações."""
    encontrados = []
    texto = _norm(" | ".join(nomes_movimentacoes))
    for padrao, sigla in RE_RECURSOS:
        if re.search(padrao, texto) and sigla not in encontrados:
            encontrados.append(sigla)
    return encontrados


def detectar_bloqueio(nomes_movimentacoes):
    return any(RE_BLOQUEIO.search(_norm(n)) for n in nomes_movimentacoes)


def detectar_revelia(nomes_movimentacoes):
    return any(RE_REVELIA.search(_norm(n)) for n in nomes_movimentacoes)


def eh_decisao_com_conteudo(nome, texto_recorte):
    """Heurística do manual: movimentação que merece análise da íntegra."""
    n = _norm(nome or "")
    chaves = ["sentenca", "acordao", "despacho", "decisao", "julgamento", "tutela"]
    if any(k in n for k in chaves):
        return True
    t = _norm(texto_recorte or "")[:4000]
    return bool(t) and any(k in t for k in ("julgo", "acordam", "d e c i s a o", "dispositivo"))
