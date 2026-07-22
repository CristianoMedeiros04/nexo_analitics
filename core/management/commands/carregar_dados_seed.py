"""
Comando para carregar os dados de teste (seed) a partir do arquivo SQLite
``Banco_de_Dados.db`` empacotado no repositório para o banco configurado
atualmente (MySQL em produção).

Uso:
    python manage.py carregar_dados_seed
    python manage.py carregar_dados_seed --arquivo /caminho/para/base.db
    python manage.py carregar_dados_seed --limpar   # apaga antes de inserir

Os dados originais foram criados apenas para testes. Posteriormente os
registros serão populados a partir do JUSCONTRO com análise por IA.
"""

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.models import Processo

# Mapeamento: coluna na tabela "Página1" do SQLite -> campo do model Processo.
COLUNA_PARA_CAMPO = {
    "Número do processo": "numero_processo",
    "Advogados polo ativo": "advogados_polo_ativo",
    "Advogados polo passivo": "advogados_polo_passivo",
    "Assuntos": "assuntos",
    "Classe": "classe",
    "CNPJs": "cnpjs",
    "Partes polo ativo": "partes_polo_ativo",
    "Partes polo passivo": "partes_polo_passivo",
    "Nome / CPF": "nome_cpf",
    "Comarca": "comarca",
    "UF": "uf",
    "Vara": "vara",
    "Tribunal": "tribunal",
    "Data da distribuição": "data_distribuicao",
    "Data do arquivamento": "data_arquivamento",
    "Data do trânsito em julgado": "data_transito_julgado",
    "Data da sentença": "data_sentenca",
    "Data do primeiro acórdão": "data_primeiro_acordao",
    "Data do acordo": "data_acordo",
    "Fase": "fase",
    "Situação": "situacao",
    "Instância": "instancia",
    "Juízes": "juizes",
    "Tipo de cargos": "tipo_cargos",
    "Desfecho": "desfecho",
    "Decisões por instância": "decisoes_por_instancia",
    "Tipos de recursos": "tipos_recursos",
    "Tipo de alteração da condenação": "tipo_alteracao_condenacao",
    "Pedidos": "pedidos",
    "Indicativo de bloqueio?": "indicativo_bloqueio",
    "Indicativo de revelia?": "indicativo_revelia",
    "Valor de causa (R$)": "valor_causa",
    "Valor de condenação (R$)": "valor_condenacao",
    "Valor de acordo (R$)": "valor_acordo",
    "Valor de liquidação (R$)": "valor_liquidacao",
    "Valor de depósitos (R$)": "valor_depositos",
    "Valor de variação da condenação (R$)": "valor_variacao_condenacao",
}

CAMPOS_INTEIROS = {"instancia"}
CAMPOS_FLOAT = {"valor_liquidacao"}


class Command(BaseCommand):
    help = "Carrega os dados seed do SQLite Banco_de_Dados.db para o banco atual."

    def add_arguments(self, parser):
        parser.add_argument(
            "--arquivo",
            default=str(Path(settings.BASE_DIR) / "Banco_de_Dados.db"),
            help="Caminho para o arquivo SQLite de origem.",
        )
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove todos os processos existentes antes de importar.",
        )

    def _converter(self, campo, valor):
        if valor is None:
            return None
        if campo in CAMPOS_INTEIROS:
            try:
                return int(float(valor))
            except (TypeError, ValueError):
                return None
        if campo in CAMPOS_FLOAT:
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None
        return str(valor)

    @transaction.atomic
    def handle(self, *args, **options):
        arquivo = Path(options["arquivo"])
        if not arquivo.exists():
            raise CommandError(f"Arquivo SQLite não encontrado: {arquivo}")

        con = sqlite3.connect(str(arquivo))
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        try:
            cur.execute('SELECT * FROM "Página1"')
        except sqlite3.OperationalError as exc:
            raise CommandError(f"Erro lendo tabela Página1: {exc}")

        linhas = cur.fetchall()
        colunas_disponiveis = {desc[0] for desc in cur.description}
        con.close()

        if options["limpar"]:
            apagados = Processo.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Removidos {apagados} registros existentes."))

        mapeamento = {
            col: campo
            for col, campo in COLUNA_PARA_CAMPO.items()
            if col in colunas_disponiveis
        }

        objetos = []
        ignorados = 0
        for linha in linhas:
            dados = {}
            for col, campo in mapeamento.items():
                dados[campo] = self._converter(campo, linha[col])

            numero = dados.get("numero_processo")
            if not numero:
                ignorados += 1
                continue
            objetos.append(Processo(**dados))

        update_fields = [c for c in mapeamento.values() if c != "numero_processo"]
        bulk_kwargs = {"update_conflicts": True, "update_fields": update_fields}
        # MySQL usa ON DUPLICATE KEY UPDATE e NÃO aceita unique_fields no upsert;
        # SQLite/PostgreSQL exigem unique_fields. Ajusta conforme o backend.
        if connection.vendor != "mysql":
            bulk_kwargs["unique_fields"] = ["numero_processo"]

        Processo.objects.bulk_create(objetos, **bulk_kwargs)

        self.stdout.write(
            self.style.SUCCESS(
                f"Importados/atualizados {len(objetos)} processos "
                f"({ignorados} ignorados sem número). "
                f"Total no banco: {Processo.objects.count()}."
            )
        )
