"""
Sincroniza processos do ControlJus (contrato 044312) com o banco.

Fluxo por processo:
1. metadados objetivos (GET /Processos/{id}) → campos do Processo;
2. movimentações incrementais (idempotente por andamento_id);
3. extração de eventos (sentença/acórdão/trânsito/acordo/arquivamento)
   → tabela Decisao + datas legadas + desfecho objetivo quando o nome
   da movimentação já o revela;
4. materialização das colunas legadas (recursos, bloqueio, revelia...).

A análise de ÍNTEGRAS por IA fica no comando ``ia_analisar`` (separado
para controlar custo/limite de tokens).
"""

import re
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Decisao, Movimentacao, Processo, SincronizacaoLog
from core.services import extracao
from core.services.controljus import ControlJusClient
from core.services.materializacao import materializar_processo


def _data_br(iso_str):
    """ISO ('2023-07-11T00:00:00') -> '11/07/2023' (formato legado)."""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(str(iso_str)[:19]).strftime("%d/%m/%Y")
    except ValueError:
        return None


def _dt(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_str)[:19])
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        return None


def _valor_br(numero):
    if numero in (None, "", 0):
        return None
    try:
        return f"R$ {float(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return None


def _limpar_envolvidos(texto):
    """'FULANO - Autor(a), BELTRANO - Réu' -> 'FULANO, BELTRANO'."""
    if not texto:
        return None
    nomes = [t.split(" - ")[0].strip() for t in texto.split(",")]
    return ", ".join(n for n in nomes if n) or None


def _grau_da_fonte(descricao_fonte):
    d = (descricao_fonte or "").lower()
    if "tst" in d:
        return 3
    if "2ª" in d or "2a" in d or "segunda" in d:
        return 2
    return 1


class Command(BaseCommand):
    help = "Sincroniza processos e movimentações do ControlJus."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=None,
                            help="Sincroniza apenas N processos (teste/amostra).")
        parser.add_argument("--movs-max", type=int, default=400,
                            help="Máximo de movimentações por processo (padrão 400).")
        parser.add_argument("--ids", type=str, default=None,
                            help="IDs ControlJus específicos, separados por vírgula.")

    def handle(self, *args, **options):
        log = SincronizacaoLog.objects.create(comando="cj_sincronizar")
        stats = {"processos": 0, "criados": 0, "movs_novas": 0, "decisoes": 0, "erros": 0}
        try:
            cliente = ControlJusClient()
            if options["ids"]:
                ids = [int(x) for x in options["ids"].split(",")]
            else:
                ids = [item["id"] for item in cliente.listar_todos_processos()]
                self.stdout.write(f"Universo no ControlJus: {len(ids)} processos.")
            if options["limite"]:
                ids = ids[: options["limite"]]

            for i, pasta_id in enumerate(ids, 1):
                try:
                    self._sincronizar_um(cliente, pasta_id, options["movs_max"], stats)
                except Exception as exc:  # não deixa 1 processo derrubar o lote
                    stats["erros"] += 1
                    self.stderr.write(f"  ERRO em {pasta_id}: {exc}")
                if i % 25 == 0:
                    self.stdout.write(f"  ... {i}/{len(ids)} processos")

            log.status = "sucesso" if stats["erros"] == 0 else "parcial"
        except Exception as exc:
            log.status = "erro"
            stats["excecao"] = str(exc)[:500]
            raise
        finally:
            log.fim = timezone.now()
            log.detalhes = stats
            log.save()
            self.stdout.write(self.style.SUCCESS(f"Sincronização: {stats}"))

    # ------------------------------------------------------------------
    @transaction.atomic
    def _sincronizar_um(self, cliente, pasta_id, movs_max, stats):
        det = cliente.detalhe_processo(pasta_id)
        if not det:
            return
        cnj = det.get("numeroCNJ") or det.get("nome")
        if not cnj:
            return
        cnj_norm = re.sub(r"\D", "", cnj)

        proc = (
            Processo.objects.filter(controljus_id=pasta_id).first()
            or Processo.objects.filter(cnj_normalizado=cnj_norm).first()
            or Processo.objects.filter(numero_processo=cnj).first()
        )
        criado = False
        if proc is None:
            proc = Processo(numero_processo=cnj, origem="controljus", desfecho="Pendente")
            criado = True

        # ---------- metadados objetivos (API é fonte fresca)
        cidade = det.get("cidade") or {}
        estado = (cidade.get("estado") or {}).get("sigla") or {}
        orgao = det.get("orgao") or {}
        assuntos = det.get("assuntosProcessos") or []

        proc.controljus_id = pasta_id
        proc.cnj_normalizado = cnj_norm
        proc.uf = estado.get("id") or proc.uf
        proc.comarca = cidade.get("nome") or det.get("foro") or proc.comarca
        proc.vara = det.get("orgaoJulgador") or proc.vara
        proc.tribunal = orgao.get("sigla") or proc.tribunal
        proc.classe = (det.get("classeProcessual") or {}).get("nome") or proc.classe
        proc.instancia = (det.get("instancia") or {}).get("id") or proc.instancia
        proc.situacao = (det.get("status") or {}).get("nome") or proc.situacao
        proc.data_distribuicao = _data_br(det.get("dataDistribuicao")) or proc.data_distribuicao
        proc.data_ultimo_movimento = _data_br(det.get("dataUltimaMovimentacao")) or proc.data_ultimo_movimento
        if assuntos:
            proc.assuntos = ", ".join(
                a["assunto"]["nome"] for a in assuntos if (a.get("assunto") or {}).get("nome")
            ) or proc.assuntos
        proc.partes_polo_ativo = _limpar_envolvidos(det.get("envolvidosAtivos")) or proc.partes_polo_ativo
        proc.partes_polo_passivo = _limpar_envolvidos(det.get("envolvidosPassivos")) or proc.partes_polo_passivo
        proc.advogados_polo_ativo = _limpar_envolvidos(det.get("advogadosAtivo")) or proc.advogados_polo_ativo
        proc.advogados_polo_passivo = _limpar_envolvidos(det.get("advogadosPassivo")) or proc.advogados_polo_passivo
        proc.cnpjs = det.get("cpfCnpjPoloPassivo") or proc.cnpjs
        if det.get("envolvidosAtivos") and det.get("cpfCnpjPoloAtivo"):
            nome_ativo = _limpar_envolvidos(det["envolvidosAtivos"]).split(",")[0]
            proc.nome_cpf = f"{nome_ativo} / {det['cpfCnpjPoloAtivo']}"
        proc.segredo_justica = "Sim" if det.get("segredoDeJustica") else (proc.segredo_justica or "Não")
        proc.justica_gratuita = "Sim" if det.get("concessaoGratuidade") else (proc.justica_gratuita or "Não")
        proc.valor_causa = _valor_br(det.get("valorCausa")) or proc.valor_causa
        proc.valor_acordo = _valor_br(det.get("valorAcordo")) or proc.valor_acordo
        proc.ultima_sincronizacao = timezone.now()
        if not proc.fase:
            proc.fase = "Execução" if "cumprimento" in (proc.classe or "").lower() else "Conhecimento"
        proc.save()
        stats["processos"] += 1
        stats["criados"] += int(criado)

        # ---------- movimentações (incremental por andamento_id)
        existentes = set(
            Movimentacao.objects.filter(processo=proc).values_list("andamento_id", flat=True)
        )
        novas = []
        for mov in cliente.movimentacoes(pasta_id, max_itens=movs_max):
            aid = mov.get("andamentoId") or mov.get("id")
            if not aid or aid in existentes:
                continue
            rec = mov.get("recorte") or {}
            novas.append(Movimentacao(
                processo=proc,
                andamento_id=aid,
                data_hora=_dt(mov.get("dataHora")),
                nome=(mov.get("nome") or "")[:5000],
                tipo_andamento=((mov.get("tipoAndamento") or {}).get("nome") or "")[:100],
                descricao_fonte=(mov.get("descricaoFonte") or "")[:150],
                recorte_texto=rec.get("textoLimpo") or "",
                recorte_diario=(rec.get("diarioNome") or "")[:150],
                recorte_disponibilizacao=_dt(rec.get("disponibilizacaoDataHora")),
            ))
        if novas:
            Movimentacao.objects.bulk_create(novas, ignore_conflicts=True)
            stats["movs_novas"] += len(novas)

        # ---------- extração de eventos e datas
        movs = list(Movimentacao.objects.filter(processo=proc).order_by("data_hora"))
        datas = {}
        ultimo_resultado = ("", None)  # (rotulo, data)
        for m in movs:
            tipo = extracao.classificar_ato(m.nome)
            # publicações DJEN têm nome numérico, mas o TEXTO pode conter a decisão
            if not tipo and m.recorte_texto and extracao.eh_decisao_com_conteudo(m.nome, m.recorte_texto):
                tipo = "decisao"
            if not tipo:
                continue
            resultado = extracao.inferir_resultado(m.nome)
            texto = m.recorte_texto if extracao.eh_decisao_com_conteudo(m.nome, m.recorte_texto) else ""
            decisao, criada = Decisao.objects.get_or_create(
                processo=proc, movimentacao=m, tipo_ato=tipo,
                defaults={
                    "data": m.data_hora,
                    "grau": _grau_da_fonte(m.descricao_fonte),
                    "texto": texto,
                    "fonte_texto": "controljus" if texto else "",
                    "resultado": resultado,
                    "status_analise": "pendente" if texto else "sem_texto",
                },
            )
            if criada:
                stats["decisoes"] += 1
            chave = {
                "sentenca": "data_sentenca",
                "acordao": "data_primeiro_acordao",
                "transito": "data_transito_julgado",
                "arquivamento": "data_arquivamento",
                "homologacao_acordo": "data_acordo",
            }.get(tipo)
            if chave and m.data_hora and chave not in datas:
                datas[chave] = m.data_hora.strftime("%d/%m/%Y")
            if resultado and m.data_hora and (
                ultimo_resultado[1] is None or m.data_hora > ultimo_resultado[1]
            ):
                ultimo_resultado = (resultado, m.data_hora)

        alterados = []
        for campo, valor in datas.items():
            if getattr(proc, campo) != valor and valor:
                setattr(proc, campo, valor)
                alterados.append(campo)

        # desfecho objetivo: acordo prevalece; senão o último resultado extraído
        if any(extracao.classificar_ato(m.nome) == "homologacao_acordo" for m in movs):
            novo_desfecho = "Acordo"
        else:
            novo_desfecho = ultimo_resultado[0]
        if novo_desfecho and proc.desfecho in (None, "", "Pendente"):
            proc.desfecho = novo_desfecho
            alterados.append("desfecho")

        # último movimento (ignora nomes puramente numéricos — IDs de publicação DJEN)
        if movs:
            candidatos = [m for m in movs if m.data_hora and not m.nome.strip().isdigit()]
            mais_recente = max(candidatos or [m for m in movs if m.data_hora],
                               key=lambda m: m.data_hora, default=None)
            if mais_recente:
                if proc.ultimo_movimento != mais_recente.nome:
                    proc.ultimo_movimento = mais_recente.nome
                    alterados.append("ultimo_movimento")
                data_um = mais_recente.data_hora.strftime("%d/%m/%Y")
                if proc.data_ultimo_movimento != data_um:
                    proc.data_ultimo_movimento = data_um
                    alterados.append("data_ultimo_movimento")

        if alterados:
            proc.save(update_fields=list(set(alterados)))

        materializar_processo(proc)
