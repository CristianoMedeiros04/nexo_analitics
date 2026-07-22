"""
Semeia o catálogo canônico de pedidos (PedidoCatalogo) a partir do
fixture ``core/fixtures/catalogo_pedidos.json`` (288 tipos extraídos da
planilha-base da empresa de jurimetria).
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import PedidoCatalogo


class Command(BaseCommand):
    help = "Semeia o catálogo padronizado de pedidos a partir da planilha-base."

    def handle(self, *args, **options):
        caminho = Path(settings.BASE_DIR) / "core" / "fixtures" / "catalogo_pedidos.json"
        dados = json.loads(caminho.read_text())

        criados = 0
        for item in dados:
            _, criado = PedidoCatalogo.objects.update_or_create(
                nome=item["nome"],
                defaults={"ocorrencias_base": item.get("ocorrencias", 0)},
            )
            criados += int(criado)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo: {criados} novos, total {PedidoCatalogo.objects.count()}."
            )
        )
