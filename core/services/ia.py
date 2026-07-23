"""
Análise de decisões judiciais com IA (DeepSeek ou Claude/Anthropic).

Recebe a íntegra de uma decisão (recorte DJEN via ControlJus) e devolve um
JSON estruturado com:
- desfecho do processo (vocabulário fechado de referência);
- pedidos identificados, SEMPRE normalizados contra o catálogo canônico
  (evita o mesmo pedido com nomes diferentes);
- resultado por pedido (DEFERIMENTO / INDEFERIMENTO / DEFERIMENTO PARCIAL);
- valores, magistrado, revelia, fundamentação resumida.

Provedor escolhido por variável de ambiente (nesta ordem):
- DEEPSEEK_API_KEY   → API DeepSeek (OpenAI-compatível, modo JSON)
- ANTHROPIC_API_KEY  → Claude API (structured outputs)

Config adicional:
- IA_MODELO (padrão: deepseek-chat no DeepSeek; claude-opus-4-8 na Anthropic)
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODELO_DEEPSEEK = "deepseek-chat"
MODELO_ANTHROPIC = "claude-opus-4-8"

DESFECHOS_PROCESSO = [
    "Acordo", "Parcialmente Procedente", "Improcedente", "Procedente",
    "Indeferimento da Petição Inicial", "Arquivamento Ausência do Reclamante",
    "Desistência", "Ausência de Pressupostos Processuais", "Segurança (denegação)",
    "Perempção, litispendência ou coisa julgada", "Ausência das Condições da Ação",
    "Pendente", "Outros",
]
RESULTADOS_PEDIDO = ["DEFERIMENTO", "INDEFERIMENTO", "DEFERIMENTO PARCIAL", "PLEITEADO", "INDETERMINADO"]

SCHEMA_ANALISE = {
    "type": "object",
    "properties": {
        "tipo_ato": {
            "type": "string",
            "enum": ["sentenca", "acordao", "decisao", "despacho", "homologacao_acordo", "outro"],
            "description": "Tipo do ato decisório analisado",
        },
        "desfecho_processo": {
            "type": ["string", "null"],
            "enum": DESFECHOS_PROCESSO + [None],
            "description": "Desfecho do processo definido por este ato, ou null se o ato não define desfecho",
        },
        "pedidos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nome_catalogo": {
                        "type": "string",
                        "description": "Nome EXATO de um pedido do catálogo fornecido. Use SEMPRE o catálogo; só crie nome novo se realmente não houver equivalente.",
                    },
                    "resultado": {"type": "string", "enum": RESULTADOS_PEDIDO},
                    "valor": {"type": ["number", "null"], "description": "Valor em R$ atribuído ao pedido, se mencionado"},
                    "fundamentacao": {"type": "string", "description": "Resumo curto (1-2 frases) da fundamentação para este pedido"},
                },
                "required": ["nome_catalogo", "resultado", "valor", "fundamentacao"],
                "additionalProperties": False,
            },
        },
        "magistrado": {"type": ["string", "null"], "description": "Nome do juiz/relator que assinou, se identificável"},
        "revelia": {"type": ["boolean", "null"], "description": "Há decretação de revelia neste ato?"},
        "valor_condenacao": {"type": ["number", "null"], "description": "Valor total da condenação em R$, se fixado"},
        "valor_acordo": {"type": ["number", "null"], "description": "Valor do acordo homologado em R$, se houver"},
        "justica_gratuita": {"type": ["boolean", "null"], "description": "Concessão de justiça gratuita neste ato"},
        "fundamentacao_geral": {"type": "string", "description": "Resumo geral da fundamentação do ato (2-4 frases)"},
        "confianca": {"type": "number", "description": "Confiança global da análise, de 0 a 1"},
    },
    "required": [
        "tipo_ato", "desfecho_processo", "pedidos", "magistrado", "revelia",
        "valor_condenacao", "valor_acordo", "justica_gratuita",
        "fundamentacao_geral", "confianca",
    ],
    "additionalProperties": False,
}

CAMPOS_OBRIGATORIOS = list(SCHEMA_ANALISE["required"])


def provedor_disponivel():
    """Retorna 'deepseek', 'anthropic' ou None conforme as chaves configuradas."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _carregar_catalogo():
    caminho = Path(settings.BASE_DIR) / "core" / "fixtures" / "catalogo_pedidos.json"
    dados = json.loads(caminho.read_text())
    return [item["nome"] for item in dados]


def montar_system_prompt():
    """System prompt estável com vocabulários e catálogo canônico."""
    catalogo = _carregar_catalogo()
    return f"""Você é um analista de jurimetria especializado em Justiça do Trabalho brasileira.
Sua tarefa: analisar o texto de decisões judiciais (sentenças, acórdãos, decisões, homologações) e extrair dados estruturados em JSON.

REGRAS CRÍTICAS DE PADRONIZAÇÃO:
1. Todo pedido identificado DEVE ser mapeado para o nome EXATO de um item do CATÁLOGO DE PEDIDOS abaixo. Nunca invente variações: "Hora extra", "horas extraordinárias" e "HE" são todos "Horas Extras".
2. Só use um nome fora do catálogo se genuinamente não existir equivalente — e nesse caso use um nome curto, no singular/plural conforme o padrão do catálogo.
3. Resultado por pedido: DEFERIMENTO (julgado procedente), INDEFERIMENTO (improcedente/rejeitado), DEFERIMENTO PARCIAL (acolhido em parte), PLEITEADO (apenas mencionado como pedido, sem julgamento neste ato), INDETERMINADO (impossível determinar).
4. Desfechos de processo válidos: {json.dumps(DESFECHOS_PROCESSO, ensure_ascii=False)}. "Parcialmente Procedente" quando ao menos um pedido é acolhido e outro rejeitado.
5. Não confunda o dispositivo (o que foi decidido) com o relatório (o que foi pedido). O resultado vem do DISPOSITIVO.
6. Em acórdãos, o resultado reflete o julgamento do recurso ("nego provimento" mantém a decisão anterior; "dou provimento" reforma).
7. Se o texto for apenas uma intimação sem conteúdo decisório, retorne tipo_ato="outro", pedidos=[] e confiança baixa.

FORMATO DE SAÍDA — responda APENAS com um objeto JSON válido, sem markdown, exatamente nesta estrutura:
{{
  "tipo_ato": "sentenca|acordao|decisao|despacho|homologacao_acordo|outro",
  "desfecho_processo": "<um dos desfechos válidos>" ou null,
  "pedidos": [{{"nome_catalogo": "...", "resultado": "DEFERIMENTO|INDEFERIMENTO|DEFERIMENTO PARCIAL|PLEITEADO|INDETERMINADO", "valor": 1234.56 ou null, "fundamentacao": "..."}}],
  "magistrado": "NOME" ou null,
  "revelia": true/false/null,
  "valor_condenacao": numero ou null,
  "valor_acordo": numero ou null,
  "justica_gratuita": true/false/null,
  "fundamentacao_geral": "...",
  "confianca": 0.0 a 1.0
}}

CATÁLOGO DE PEDIDOS ({len(catalogo)} itens):
{chr(10).join('- ' + n for n in catalogo)}
"""


class AnalisadorIA:
    def __init__(self, modelo=None):
        self.provedor = provedor_disponivel()
        if not self.provedor:
            raise RuntimeError(
                "Nenhuma chave de IA configurada — defina DEEPSEEK_API_KEY "
                "(ou ANTHROPIC_API_KEY) para habilitar a análise."
            )
        self.system_text = montar_system_prompt()

        if self.provedor == "deepseek":
            self.api_key = os.environ["DEEPSEEK_API_KEY"]
            self.modelo = modelo or os.environ.get("IA_MODELO", MODELO_DEEPSEEK)
            if not self.modelo.startswith("deepseek"):
                self.modelo = MODELO_DEEPSEEK
        else:
            import anthropic

            self.client = anthropic.Anthropic(
                api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=4
            )
            self.modelo = modelo or os.environ.get("IA_MODELO", MODELO_ANTHROPIC)
            if self.modelo.startswith("deepseek"):
                self.modelo = MODELO_ANTHROPIC
            self.system = [{
                "type": "text",
                "text": self.system_text,
                "cache_control": {"type": "ephemeral"},
            }]

    # ------------------------------------------------------------- público
    def analisar_texto(self, texto_decisao, contexto_processo=""):
        """Analisa a íntegra de uma decisão. Retorna dict validado."""
        texto = texto_decisao[:60000]
        mensagem = (
            (f"CONTEXTO DO PROCESSO:\n{contexto_processo}\n\n" if contexto_processo else "")
            + f"TEXTO DA DECISÃO/PUBLICAÇÃO:\n{texto}"
        )
        if self.provedor == "deepseek":
            dados = self._chamar_deepseek(mensagem)
        else:
            dados = self._chamar_anthropic(mensagem)
        self._validar(dados)
        dados["_modelo"] = f"{self.provedor}:{self.modelo}"
        return dados

    # ------------------------------------------------------------ deepseek
    def _chamar_deepseek(self, mensagem, tentativa=0):
        corpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": self.system_text},
                {"role": "user", "content": mensagem},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 8000,
        }
        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=json.dumps(corpo).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and tentativa < 3:
                time.sleep(2 ** (tentativa + 1))
                return self._chamar_deepseek(mensagem, tentativa + 1)
            raise RuntimeError(f"DeepSeek HTTP {e.code}: {e.read().decode()[:200]}")

        conteudo = payload["choices"][0]["message"]["content"]
        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError:
            if tentativa < 1:
                return self._chamar_deepseek(
                    mensagem + "\n\nATENÇÃO: responda somente com JSON válido.",
                    tentativa + 1,
                )
            raise RuntimeError(f"DeepSeek retornou JSON inválido: {conteudo[:200]}")

        uso = payload.get("usage") or {}
        dados["_usage"] = {
            "input_tokens": uso.get("prompt_tokens"),
            "output_tokens": uso.get("completion_tokens"),
            "cache_read": (uso.get("prompt_cache_hit_tokens") or 0),
        }
        return dados

    # ----------------------------------------------------------- anthropic
    def _chamar_anthropic(self, mensagem):
        resposta = self.client.messages.create(
            model=self.modelo,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=self.system,
            messages=[{"role": "user", "content": mensagem}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA_ANALISE}},
        )
        if resposta.stop_reason == "refusal":
            raise RuntimeError("A análise foi recusada pelo modelo (refusal).")
        if resposta.stop_reason == "max_tokens":
            raise RuntimeError("Resposta truncada (max_tokens) — texto muito longo.")
        texto_json = next(b.text for b in resposta.content if b.type == "text")
        dados = json.loads(texto_json)
        dados["_usage"] = {
            "input_tokens": resposta.usage.input_tokens,
            "output_tokens": resposta.usage.output_tokens,
            "cache_read": getattr(resposta.usage, "cache_read_input_tokens", 0),
        }
        return dados

    # ------------------------------------------------------------ validação
    @staticmethod
    def _validar(dados):
        """Valida/normaliza a resposta (essencial no modo JSON do DeepSeek)."""
        faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados]
        for campo in faltando:
            dados[campo] = [] if campo == "pedidos" else None
        if not isinstance(dados.get("pedidos"), list):
            dados["pedidos"] = []
        pedidos_ok = []
        for p in dados["pedidos"]:
            if not isinstance(p, dict) or not p.get("nome_catalogo"):
                continue
            if p.get("resultado") not in RESULTADOS_PEDIDO:
                p["resultado"] = "INDETERMINADO"
            if not isinstance(p.get("valor"), (int, float)):
                p["valor"] = None
            p.setdefault("fundamentacao", "")
            pedidos_ok.append(p)
        dados["pedidos"] = pedidos_ok
        if dados.get("desfecho_processo") not in DESFECHOS_PROCESSO + [None]:
            dados["desfecho_processo"] = None
        try:
            dados["confianca"] = max(0.0, min(1.0, float(dados.get("confianca") or 0)))
        except (TypeError, ValueError):
            dados["confianca"] = 0.0
