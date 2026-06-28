#!/bin/bash
# Encerra o script se qualquer comando falhar
set -e

echo "=> Iniciando configuração do Django no Docker..."

echo "=> Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "=> Aplicando migrações do banco de dados..."
python manage.py migrate --noinput

echo "=> Iniciando a aplicação com Gunicorn..."
exec "$@"
