#!/bin/bash
# Script para backup do SQLite, Arquivos de Media e Token do Google

# Configuração de data e hora para o nome do arquivo
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/app/backups"
BACKUP_FILE="${BACKUP_DIR}/backup_${DATE}.tar.gz"

# Cria o diretório de backups caso não exista
mkdir -p ${BACKUP_DIR}

echo "=> Iniciando backup em ${BACKUP_FILE}..."

# Executa o backup compactando a pasta db/ (SQLite), media/ e token.json
tar -czf ${BACKUP_FILE} -C /app db/ media/ token.json

echo "=> Backup concluído com sucesso!"
echo "=> Mantenha o arquivo ${BACKUP_FILE} em segurança."

# Regra para manter apenas os últimos 7 backups (limpeza automática)
ls -t ${BACKUP_DIR}/backup_*.tar.gz | tail -n +8 | xargs -r rm --
echo "=> Backups antigos removidos (mantidos apenas os 7 mais recentes)."
