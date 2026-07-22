#!/usr/bin/env bash
set -e

echo ">> Aplicando migrations..."
python manage.py migrate --noinput

echo ">> Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo ">> Semeando catálogo de pedidos..."
python manage.py seed_catalogo_pedidos || echo "!! Falha no catálogo (seguindo)"

if [ "${IMPORT_PLANILHA:-true}" = "true" ]; then
  echo ">> Importando planilha-base (idempotente)..."
  python manage.py importar_planilha || echo "!! Falha na planilha (seguindo)"
fi

if [ "${SEED_DATA:-false}" = "true" ]; then
  echo ">> Carregando dados seed SQLite (SEED_DATA=true)..."
  python manage.py carregar_dados_seed || echo "!! Falha no seed (seguindo)"
fi

echo ">> Iniciando Gunicorn na porta ${PORT:-8000}..."
exec gunicorn jurimetria.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
