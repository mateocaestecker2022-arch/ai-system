#!/bin/bash
# Setup serveur Hetzner — Ubuntu 22.04
# Usage : bash setup.sh

set -e

APP_DIR="/opt/ai-system"
APP_USER="ai-system"

echo "==> Update système"
apt-get update && apt-get upgrade -y

echo "==> Dépendances système"
apt-get install -y python3 python3-venv python3-pip nginx git curl

echo "==> Création utilisateur dédié"
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER

echo "==> Copie du code"
mkdir -p $APP_DIR
cp -r . $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

echo "==> Environnement Python"
sudo -u $APP_USER python3 -m venv $APP_DIR/.venv
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt

echo "==> Fichier .env"
if [ ! -f $APP_DIR/.env ]; then
    cp $APP_DIR/.env.example $APP_DIR/.env
    echo "⚠  Remplis $APP_DIR/.env avec ta clé ANTHROPIC_API_KEY"
fi

echo "==> Service systemd"
cp $APP_DIR/deploy/ai-system.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ai-system
systemctl restart ai-system

echo "==> Nginx"
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/ai-system
ln -sf /etc/nginx/sites-available/ai-system /etc/nginx/sites-enabled/ai-system
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "✅ Setup terminé. API disponible sur http://$(hostname -I | awk '{print $1}')"
