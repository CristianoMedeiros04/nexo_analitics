"""
Orquestrador da atualização semanal (cron do Railway).

Sequência:
1. cj_sincronizar   — atualiza metadados, movimentações e eventos de todos
                      os processos do ControlJus (incremental);
2. ia_analisar      — analisa com IA as novas decisões que têm texto
                      (pulado silenciosamente se ANTHROPIC_API_KEY ausente);

A materialização das colunas legadas acontece dentro de cada etapa.
Projetado para rodar como serviço cron: executa e termina.
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import SincronizacaoLog


class Command(BaseCommand):
    help = "Atualização semanal: sincroniza ControlJus e roda análise IA."

    def add_arguments(self, parser):
        parser.add_argument("--limite-ia", type=int, default=200,
                            help="Máximo de decisões analisadas por IA nesta execução.")

    def handle(self, *args, **options):
        log = SincronizacaoLog.objects.create(comando="sync_semanal")
        etapas = {}
        try:
            self.stdout.write("=== [1/2] Sincronização ControlJus ===")
            call_command("cj_sincronizar")
            etapas["cj_sincronizar"] = "ok"

            self.stdout.write("=== [2/2] Análise IA ===")
            if os.environ.get("ANTHROPIC_API_KEY"):
                call_command("ia_analisar", limite=options["limite_ia"])
                etapas["ia_analisar"] = "ok"
            else:
                etapas["ia_analisar"] = "pulado (ANTHROPIC_API_KEY ausente)"
                self.stdout.write(self.style.WARNING(
                    "ANTHROPIC_API_KEY ausente — etapa de IA pulada."
                ))

            log.status = "sucesso"
        except Exception as exc:
            log.status = "erro"
            etapas["excecao"] = str(exc)[:500]
            raise
        finally:
            log.fim = timezone.now()
            log.detalhes = etapas
            log.save()
            self.stdout.write(self.style.SUCCESS(f"sync_semanal: {etapas}"))
