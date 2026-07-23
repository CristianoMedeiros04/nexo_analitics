"""
Importa a planilha-base (919 processos, fixture JSON) para o banco.

- Cria processos ausentes e preenche campos vazios dos existentes
  (nunca sobrescreve dado mais novo vindo do ControlJus/IA, a menos
  que --sobrescrever seja passado).
- Normaliza os pedidos contra o catálogo e cria PedidoProcesso a partir
  da coluna "TipoPedido / Valor / Desfecho" (valores e desfechos por
  pedido) com fallback para a coluna "Pedidos".
"""

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import PedidoProcesso, Processo
from core.services.normalizacao import NormalizadorPedidos

# Coluna da planilha -> campo do model
MAPA = {
    "Número do processo": "numero_processo",
    "Advogados polo ativo": "advogados_polo_ativo",
    "Advogados polo passivo": "advogados_polo_passivo",
    "Assuntos": "assuntos",
    "Classe": "classe",
    "CNPJs": "cnpjs",
    "Comarca": "comarca",
    "Data da distribuição": "data_distribuicao",
    "Data da sentença": "data_sentenca",
    "Data de admissão / Data de demissão": "data_admissao_demissao",
    "Data do acordo": "data_acordo",
    "Data do arquivamento": "data_arquivamento",
    "Data do primeiro acórdão": "data_primeiro_acordao",
    "Data do trânsito em julgado": "data_transito_julgado",
    "Data do ultimo movimento": "data_ultimo_movimento",
    "Decisões por instância": "decisoes_por_instancia",
    "Desfecho": "desfecho",
    "Deve reembolso?": "deve_reembolso",
    "Fase": "fase",
    "Indicativo de bloqueio?": "indicativo_bloqueio",
    "Indicativo de revelia?": "indicativo_revelia",
    "Instância": "instancia",
    "Juízes": "juizes",
    "Justiça gratuita?": "justica_gratuita",
    "Nome / CPF": "nome_cpf",
    "Pagamentos de Recursos": "pagamentos_recursos",
    "Partes polo ativo": "partes_polo_ativo",
    "Partes polo passivo": "partes_polo_passivo",
    "Pedidos": "pedidos",
    "Possui pedido de substituição": "possui_pedido_substituicao",
    "Segredo de justiça?": "segredo_justica",
    "Situação": "situacao",
    "Tipo de alteração da condenação": "tipo_alteracao_condenacao",
    "Tipo de cargos": "tipo_cargos",
    "TipoPedido / Valor / Desfecho": "tipo_pedido_valor_desfecho",
    "Tipos de recursos": "tipos_recursos",
    "Tribunal": "tribunal",
    "UF": "uf",
    "Ultimo movimento": "ultimo_movimento",
    "Último salário": "ultimo_salario",
    "Valor de acordo (R$)": "valor_acordo",
    "Valor de causa (R$)": "valor_causa",
    "Valor de condenação (R$)": "valor_condenacao",
    "Valor de custas (R$)": "valor_custas",
    "Valor de depósitos (R$)": "valor_depositos",
    "Valor de diferença de custas (R$)": "valor_diferenca_custas",
    "Valor de liquidação (R$)": "valor_liquidacao",
    "Valor de variação da condenação (R$)": "valor_variacao_condenacao",
    "Vara": "vara",
}

DESFECHOS_PEDIDO_VALIDOS = {
    "PLEITEADO", "DEFERIMENTO", "INDEFERIMENTO", "DEFERIMENTO PARCIAL", "INDETERMINADO",
}

# Nome do estado -> sigla (padroniza a coluna UF; o ControlJus já entrega sigla)
UF_SIGLAS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE",
    "Tocantins": "TO",
}


def _decimal_br(valor_str):
    try:
        return Decimal(valor_str.replace(".", "").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_trios(texto):
    """
    Divide "Nome / R$ 1.234,56 / DESFECHO, Nome2 / R$ ... / ..." em trios,
    tolerando '/', '|' e vírgulas dentro dos nomes dos pedidos.

    Estratégia: divide pelo padrão monetário (R$ x,xx). O segmento após cada
    valor começa com "/ DESFECHO" e, depois de uma vírgula, traz o nome do
    trio seguinte — por isso o desfecho é CONSUMIDO do segmento antes de o
    restante virar o próximo nome.
    """
    if not texto:
        return []
    pedacos = re.split(r"(R\$\s*[\d.,]+)", texto)
    if len(pedacos) < 2:
        return []

    trios = []
    nome_atual = pedacos[0]
    for i in range(1, len(pedacos), 2):
        valor = pedacos[i]
        resto = pedacos[i + 1] if i + 1 < len(pedacos) else ""
        m = re.match(r"\s*/\s*([A-ZÀ-Ü][A-ZÀ-Ü ]*[A-ZÀ-Ü]|[A-ZÀ-Ü])?", resto)
        desfecho = (m.group(1) or "").strip() if m else ""
        proximo_nome = resto[m.end():] if m else resto
        proximo_nome = re.sub(r"^\s*,\s*", "", proximo_nome)

        if desfecho not in DESFECHOS_PEDIDO_VALIDOS:
            desfecho = "PLEITEADO" if not desfecho else "INDETERMINADO"

        nome = re.sub(r"\s*/\s*$", "", nome_atual).strip()
        nome = " ".join(nome.split())
        if nome:
            trios.append((nome, _decimal_br(valor.replace("R$", "").strip()), desfecho))
        nome_atual = proximo_nome
    return trios


class Command(BaseCommand):
    help = "Importa a planilha-base (fixture JSON) para o banco."

    def add_arguments(self, parser):
        parser.add_argument("--sobrescrever", action="store_true",
                            help="Sobrescreve campos já preenchidos com os valores da planilha.")
        parser.add_argument("--sem-pedidos", action="store_true",
                            help="Não gera PedidoProcesso normalizados.")

    @transaction.atomic
    def handle(self, *args, **options):
        caminho = Path(settings.BASE_DIR) / "core" / "fixtures" / "planilha_base.json"
        registros = json.loads(caminho.read_text())
        sobrescrever = options["sobrescrever"]

        existentes = {p.numero_processo: p for p in Processo.objects.all()}
        criados = atualizados = 0

        for reg in registros:
            numero = reg.get("Número do processo")
            if not numero:
                continue
            dados = {campo: reg.get(col) for col, campo in MAPA.items() if campo != "numero_processo"}
            # tipos especiais
            if dados.get("uf"):
                dados["uf"] = UF_SIGLAS.get(dados["uf"], dados["uf"])
            if dados.get("instancia") is not None:
                try:
                    dados["instancia"] = int(float(dados["instancia"]))
                except (TypeError, ValueError):
                    dados["instancia"] = None
            if dados.get("valor_liquidacao") is not None:
                try:
                    dados["valor_liquidacao"] = float(
                        str(dados["valor_liquidacao"]).replace("R$", "").replace(".", "").replace(",", ".")
                    )
                except ValueError:
                    dados["valor_liquidacao"] = None

            proc = existentes.get(numero)
            if proc is None:
                proc = Processo(
                    numero_processo=numero,
                    origem="planilha",
                    cnj_normalizado=re.sub(r"\D", "", numero),
                    **{k: v for k, v in dados.items() if v is not None},
                )
                proc.save()
                existentes[numero] = proc
                criados += 1
            else:
                alterados = []
                if not proc.cnj_normalizado:
                    proc.cnj_normalizado = re.sub(r"\D", "", numero)
                    alterados.append("cnj_normalizado")
                for campo, valor in dados.items():
                    if valor is None:
                        continue
                    atual = getattr(proc, campo)
                    if sobrescrever or atual in (None, ""):
                        if atual != valor:
                            setattr(proc, campo, valor)
                            alterados.append(campo)
                if alterados:
                    proc.save(update_fields=alterados)
                    atualizados += 1

        # ---- Normalização de UF nos registros existentes (nome -> sigla)
        normalizados_uf = 0
        for nome_uf, sigla in UF_SIGLAS.items():
            normalizados_uf += Processo.objects.filter(uf=nome_uf).update(uf=sigla)
        if normalizados_uf:
            self.stdout.write(f"UF normalizada em {normalizados_uf} registros (nome -> sigla).")

        # ---- Limpeza de sobras do seed de testes (SQLite antigo):
        # registros que não estão na planilha E nunca foram vistos no
        # ControlJus são dados de teste obsoletos.
        numeros_planilha = {r["Número do processo"] for r in registros if r.get("Número do processo")}
        sobras = Processo.objects.filter(controljus_id__isnull=True).exclude(
            numero_processo__in=numeros_planilha
        )
        removidos = sobras.count()
        if removidos:
            sobras.delete()
            self.stdout.write(self.style.WARNING(
                f"Removidos {removidos} registros de teste obsoletos (seed antigo)."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Processos: {criados} criados, {atualizados} atualizados "
            f"(total no banco: {Processo.objects.count()})."
        ))

        if options["sem_pedidos"]:
            return

        # ---- Pedidos normalizados (bulk: 1 prefetch + 1 bulk_create,
        #      para o boot em produção não fazer milhares de round-trips)
        normalizador = NormalizadorPedidos()
        pares_existentes = set(
            PedidoProcesso.objects.values_list("processo_id", "catalogo_id")
        )
        novos_objetos = []
        vistos_nesta_carga = set()
        novos_catalogo = 0
        for reg in registros:
            numero = reg.get("Número do processo")
            proc = existentes.get(numero)
            if not proc:
                continue

            trios = parse_trios(reg.get("TipoPedido / Valor / Desfecho"))
            if not trios and reg.get("Pedidos"):
                trios = [(" ".join(n.split()), None, "PLEITEADO")
                         for n in str(reg["Pedidos"]).split(",") if n.strip()]

            for nome, valor, desfecho in trios:
                cat, novo = normalizador.normalizar(nome)
                if not cat:
                    continue
                novos_catalogo += int(novo)
                chave = (proc.pk, cat.pk)
                if chave in pares_existentes or chave in vistos_nesta_carga:
                    continue
                vistos_nesta_carga.add(chave)
                novos_objetos.append(PedidoProcesso(
                    processo=proc, catalogo=cat,
                    nome_original=nome[:255],
                    valor_pleiteado=valor,
                    resultado=desfecho,
                    fonte="planilha",
                ))

        if novos_objetos:
            PedidoProcesso.objects.bulk_create(
                novos_objetos, ignore_conflicts=True, batch_size=500
            )

        self.stdout.write(self.style.SUCCESS(
            f"Pedidos normalizados: {len(novos_objetos)} criados "
            f"({novos_catalogo} entradas novas no catálogo)."
        ))
