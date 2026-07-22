#!/usr/bin/env bash
set -e

echo ">> Aplicando migrations..."
python manage.py migrate --noinput

echo ">> Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

if [ "${SEED_DATA:-false}" = "true" ]; then
  echo ">> Carregando dados seed (SEED_DATA=true)..."
  python manage.py carregar_dados_seed || echo "!! Falha ao carregar seed (seguindo mesmo assim)"
fi

echo ">> Iniciando Gunicorn na porta ${PORT:-8000}..."
exec gunicorn jurimetria.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
