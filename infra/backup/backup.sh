#!/bin/bash
BACKUP_DIR="/opt/aria/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="aria_backup_${TIMESTAMP}.sql.gz"

mkdir -p $BACKUP_DIR

# Backup using docker
docker compose exec -T postgres pg_dump -U aria aria | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 7 daily backups
find $BACKUP_DIR -name "aria_backup_*.sql.gz" -mtime +7 -delete

echo "Backup saved: ${BACKUP_DIR}/${FILENAME}"
