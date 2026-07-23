"""
Mantém no banco somente os processos monitorados no ControlJus.

Remove processos que nunca foram vistos na API (controljus_id nulo) —
tipicamente registros importados da planilha de referência que não estão
no contrato de monitoramento. Idempotente; roda no boot quando
APENAS_CONTROLJUS=true.
"""

from django.core.management.base import BaseCommand

from core.models import Processo


class Command(BaseCommand):
    help = "Remove processos que não existem no ControlJus (fonte oficial dos dados)."

    def handle(self, *args, **options):
        alvo = Processo.objects.filter(controljus_id__isnull=True)
        total = alvo.count()
        if total:
            alvo.delete()
            self.stdout.write(self.style.WARNING(
                f"Removidos {total} processos sem correspondência no ControlJus."
            ))
        self.stdout.write(self.style.SUCCESS(
            f"Processos no banco (todos do ControlJus): {Processo.objects.count()}."
        ))
