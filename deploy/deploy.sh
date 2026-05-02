#!/bin/bash
# Déploiement mise à jour — à lancer depuis le serveur
# Usage : bash deploy.sh

set -e

APP_DIR="/opt/ai-system"
APP_USER="ai-system"

echo "==> Pull dernières modifications"
cd $APP_DIR
git pull origin main

echo "==> Mise à jour dépendances"
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r requirements.txt --quiet

echo "==> Redémarrage service"
systemctl restart ai-system
systemctl status ai-system --no-pager

echo "✅ Déploiement terminé"
