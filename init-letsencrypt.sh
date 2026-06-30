#!/bin/bash
# init-letsencrypt.sh — one-time bootstrap to get a real Let's Encrypt cert
# for the production nginx + certbot stack. Run once on the EC2 instance,
# from the project directory, after `deploy.sh` has set things up.
#
# Usage: ./init-letsencrypt.sh yourdomain.com you@example.com
set -euo pipefail

DOMAIN="${1:?Usage: ./init-letsencrypt.sh <domain> <email>}"
EMAIL="${2:?Usage: ./init-letsencrypt.sh <domain> <email>}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
CERT_PATH="data/certbot/conf/live/$DOMAIN"

echo "==> Rendering nginx.conf from template with domain: $DOMAIN"
sed "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf.template > nginx/nginx.conf

echo "==> Creating dummy self-signed cert so nginx can start"
mkdir -p "$CERT_PATH" data/certbot/www
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "$CERT_PATH/privkey.pem" \
    -out "$CERT_PATH/fullchain.pem" \
    -subj "/CN=localhost"

echo "==> Starting nginx with the dummy cert"
$COMPOSE up -d --no-deps nginx

echo "==> Removing the dummy cert"
rm -rf "data/certbot/conf/live" "data/certbot/conf/archive" "data/certbot/conf/renewal"

echo "==> Requesting the real certificate from Let's Encrypt"
# --entrypoint overrides the service's renewal-loop entrypoint (in
# docker-compose.prod.yml) back to plain `certbot` for this one-off call.
$COMPOSE run --rm --entrypoint certbot certbot certonly --webroot \
    -w /var/www/certbot --email "$EMAIL" -d "$DOMAIN" \
    --rsa-key-size 2048 --agree-tos --non-interactive

echo "==> Reloading nginx with the real certificate"
$COMPOSE exec nginx nginx -s reload

echo "==> Starting the certbot renewal service (checks every 12h, renews automatically)"
$COMPOSE up -d --no-deps certbot

echo "==> Done. https://$DOMAIN should now show a trusted certificate."
