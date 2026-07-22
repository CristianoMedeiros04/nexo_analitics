"""
Analisa com IA as decisões pendentes que possuem texto (recorte DJEN).

Para cada Decisao com status 'pendente' e texto:
1. chama a Claude API (structured output) via core.services.ia;
2. grava a análise em Decisao.analise_json;
3. aplica os resultados: PedidoProcesso normalizados, desfecho do processo,
   juízes, revelia, valores;
4. materializa as colunas legadas.

Uso:
    python manage.py ia_analisar --limite 50
    python manage.py ia_analisar --simular   # não chama a API, só lista
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Decisao, PedidoProcesso, SincronizacaoLog
from core.services.materializacao import materializar_processo
from core.services.normalizacao import NormalizadorPedidos


def _valor_br(numero):
    if numero in (None, ""):
        return None
    return f"R$ {float(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Command(BaseCommand):
    help = "Analisa decisões com texto pendente usando a Claude API."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=100)
        parser.add_argument("--simular", action="store_true",
                            help="Não chama a API; apenas lista o que seria analisado.")

    def handle(self, *args, **options):
        pendentes = (
            Decisao.objects.filter(status_analise="pendente")
            .exclude(texto="")
            .select_related("processo")
            .order_by("-data")[: options["limite"]]
        )
        total = pendentes.count() if hasattr(pendentes, "count") else len(pendentes)
        self.stdout.write(f"Decisões com texto pendentes de análise: {total}")

        if options["simular"]:
            for d in pendentes:
                self.stdout.write(
                    f"  [{str(d.data)[:10]}] {d.processo_id} · {d.tipo_ato} · {len(d.texto)} chars"
                )
            return

        from core.services.ia import AnalisadorIA  # exige ANTHROPIC_API_KEY

        log = SincronizacaoLog.objects.create(comando="ia_analisar")
        analisador = AnalisadorIA()
        normalizador = NormalizadorPedidos()
        stats = {"analisadas": 0, "erros": 0, "pedidos_gravados": 0, "modelo": analisador.modelo}

        for decisao in pendentes:
            try:
                contexto = (
                    f"Processo {decisao.processo.numero_processo} · "
                    f"{decisao.processo.classe or ''} · {decisao.processo.tribunal or ''} · "
                    f"Grau {decisao.grau or '?'}"
                )
                dados = analisador.analisar_texto(decisao.texto, contexto)
                self._aplicar(decisao, dados, normalizador, stats)
                stats["analisadas"] += 1
                self.stdout.write(
                    f"  OK {decisao.processo_id} · {decisao.tipo_ato} · "
                    f"{len(dados.get('pedidos', []))} pedidos · confiança {dados.get('confianca')}"
                )
            except Exception as exc:
                stats["erros"] += 1
                decisao.status_analise = "erro"
                decisao.save(update_fields=["status_analise"])
                self.stderr.write(f"  ERRO {decisao.id}: {exc}")

        log.fim = timezone.now()
        log.status = "sucesso" if stats["erros"] == 0 else "parcial"
        log.detalhes = stats
        log.save()
        self.stdout.write(self.style.SUCCESS(f"Análise IA: {stats}"))

    # ------------------------------------------------------------------
    def _aplicar(self, decisao, dados, normalizador, stats):
        proc = decisao.processo

        decisao.analise_json = dados
        decisao.status_analise = "analisado"
        decisao.modelo_ia = dados.get("_modelo", "")
        decisao.data_analise = timezone.now()
        if dados.get("desfecho_processo"):
            decisao.resultado = dados["desfecho_processo"]
        decisao.save()

        confianca = dados.get("confianca") or 0
        alterados = []

        # pedidos normalizados
        for p in dados.get("pedidos", []):
            cat, _ = normalizador.normalizar(p["nome_catalogo"])
            if not cat:
                continue
            obj, criado = PedidoProcesso.objects.get_or_create(
                processo=proc, catalogo=cat,
                defaults={
                    "nome_original": p["nome_catalogo"][:255],
                    "resultado": p["resultado"],
                    "valor_pleiteado": p.get("valor"),
                    "instancia": decisao.grau,
                    "fundamentacao": p.get("fundamentacao", "")[:2000],
                    "confianca_ia": confianca,
                    "fonte": "ia",
                    "decisao": decisao,
                },
            )
            if not criado:
                # decisão mais recente / resultado mais definitivo prevalece
                if p["resultado"] != "PLEITEADO" or obj.resultado == "PLEITEADO":
                    obj.resultado = p["resultado"]
                    obj.fundamentacao = p.get("fundamentacao", "")[:2000] or obj.fundamentacao
                    obj.instancia = decisao.grau or obj.instancia
                    obj.confianca_ia = confianca
                    obj.fonte = "ia"
                    obj.decisao = decisao
                    if p.get("valor") is not None and obj.valor_pleiteado is None:
                        obj.valor_pleiteado = p["valor"]
                    obj.save()
            stats["pedidos_gravados"] += 1

        # campos do processo (só sobrescreve com confiança razoável)
        if confianca >= 0.6:
            if dados.get("desfecho_processo") and dados["desfecho_processo"] != "Pendente":
                if proc.desfecho != dados["desfecho_processo"]:
                    proc.desfecho = dados["desfecho_processo"]
                    alterados.append("desfecho")
            if dados.get("magistrado"):
                nome = dados["magistrado"].strip().upper()
                atuais = [j.strip() for j in (proc.juizes or "").split(",") if j.strip()]
                if nome and nome not in atuais:
                    proc.juizes = ", ".join(atuais + [nome])
                    alterados.append("juizes")
            if dados.get("revelia") is True and proc.indicativo_revelia != "Sim":
                proc.indicativo_revelia = "Sim"
                alterados.append("indicativo_revelia")
            if dados.get("justica_gratuita") is True and proc.justica_gratuita != "Sim":
                proc.justica_gratuita = "Sim"
                alterados.append("justica_gratuita")
            vc = _valor_br(dados.get("valor_condenacao"))
            if vc and not proc.valor_condenacao:
                proc.valor_condenacao = vc
                alterados.append("valor_condenacao")
            va = _valor_br(dados.get("valor_acordo"))
            if va and not proc.valor_acordo:
                proc.valor_acordo = va
                alterados.append("valor_acordo")

        proc.ultima_analise_ia = timezone.now()
        alterados.append("ultima_analise_ia")
        proc.save(update_fields=list(set(alterados)))

        materializar_processo(proc)
