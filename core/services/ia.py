"""
Análise de decisões judiciais com a Claude API (Anthropic).

Recebe a íntegra de uma decisão (recorte DJEN via ControlJus) e devolve um
JSON estruturado com:
- desfecho do processo (vocabulário fechado da planilha-base);
- pedidos identificados, SEMPRE normalizados contra o catálogo canônico
  (evita o mesmo pedido com nomes diferentes);
- resultado por pedido (DEFERIMENTO / INDEFERIMENTO / DEFERIMENTO PARCIAL);
- valores, magistrado, revelia, fundamentação resumida.

Usa structured outputs (json_schema) para garantir JSON válido e prompt
caching para amortizar o custo do catálogo entre chamadas em lote.

Config por ambiente:
- ANTHROPIC_API_KEY  (obrigatória)
- IA_MODELO          (padrão: claude-opus-4-8)
"""

import json
import os
from pathlib import Path

from django.conf import settings

MODELO_PADRAO = "claude-opus-4-8"

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


def _carregar_catalogo():
    caminho = Path(settings.BASE_DIR) / "core" / "fixtures" / "catalogo_pedidos.json"
    dados = json.loads(caminho.read_text())
    return [item["nome"] for item in dados]


def montar_system_prompt():
    """System prompt estável (cacheável) com vocabulários e catálogo."""
    catalogo = _carregar_catalogo()
    return f"""Você é um analista de jurimetria especializado em Justiça do Trabalho brasileira.
Sua tarefa: analisar o texto de decisões judiciais (sentenças, acórdãos, decisões, homologações) e extrair dados estruturados.

REGRAS CRÍTICAS DE PADRONIZAÇÃO:
1. Todo pedido identificado DEVE ser mapeado para o nome EXATO de um item do CATÁLOGO DE PEDIDOS abaixo. Nunca invente variações: "Hora extra", "horas extraordinárias" e "HE" são todos "Horas Extras".
2. Só use um nome fora do catálogo se genuinamente não existir equivalente — e nesse caso use um nome curto, no singular/plural conforme o padrão do catálogo.
3. Resultado por pedido: DEFERIMENTO (julgado procedente), INDEFERIMENTO (improcedente/rejeitado), DEFERIMENTO PARCIAL (acolhido em parte), PLEITEADO (apenas mencionado como pedido, sem julgamento neste ato), INDETERMINADO (impossível determinar).
4. O desfecho do processo segue o vocabulário fechado fornecido no schema. "Parcialmente Procedente" quando ao menos um pedido é acolhido e outro rejeitado.
5. Não confunda o dispositivo (o que foi decidido) com o relatório (o que foi pedido). O resultado vem do DISPOSITIVO.
6. Em acórdãos, o resultado reflete o julgamento do recurso ("nego provimento" mantém a decisão anterior; "dou provimento" reforma).
7. Se o texto for apenas uma intimação sem conteúdo decisório, retorne tipo_ato="outro", pedidos=[] e confiança baixa.

CATÁLOGO DE PEDIDOS ({len(catalogo)} itens):
{chr(10).join('- ' + n for n in catalogo)}
"""


class AnalisadorIA:
    def __init__(self, modelo=None):
        import anthropic  # import tardio: dependência só é exigida quando usada

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada — defina a variável de ambiente "
                "para habilitar a análise por IA."
            )
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=4)
        self.modelo = modelo or os.environ.get("IA_MODELO", MODELO_PADRAO)
        self.system = [
            {
                "type": "text",
                "text": montar_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def analisar_texto(self, texto_decisao, contexto_processo=""):
        """Analisa a íntegra de uma decisão. Retorna dict validado pelo schema."""
        # decisões DJEN raramente passam de ~30k chars; trunca com margem segura
        texto = texto_decisao[:60000]
        mensagem = (
            (f"CONTEXTO DO PROCESSO:\n{contexto_processo}\n\n" if contexto_processo else "")
            + f"TEXTO DA DECISÃO/PUBLICAÇÃO:\n{texto}"
        )
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
        dados["_modelo"] = self.modelo
        dados["_usage"] = {
            "input_tokens": resposta.usage.input_tokens,
            "output_tokens": resposta.usage.output_tokens,
            "cache_read": getattr(resposta.usage, "cache_read_input_tokens", 0),
        }
        return dados
