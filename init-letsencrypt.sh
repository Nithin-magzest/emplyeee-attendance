#!/bin/bash
# init-letsencrypt.sh — one-time bootstrap to get a real Let's Encrypt cert
# for the production nginx + certbot stack. Run once on the EC2 instance,
# from the project directory, after `deploy.sh` has set things up.
#
# Usage: sudo ./init-letsencrypt.sh yourdomain.com you@example.com
set -euo pipefail

DOMAIN="${1:?Usage: ./init-letsencrypt.sh <domain> <email>}"
EMAIL="${2:?Usage: ./init-letsencrypt.sh <domain> <email>}"
APP_DIR="/opt/employee-attendance"
APP_USER="attendance"
COMPOSE="podman-compose -f compose.yaml -f compose.prod.yaml"
CERT_PATH="data/certbot/conf/live/$DOMAIN"

# The stack runs as rootless Podman under $APP_USER (see deploy.sh), so
# every compose call here needs to run as that user with its runtime dir,
# not as root (this script is invoked via sudo).
APP_UID="$(id -u "$APP_USER")"
run_as_app() {
    runuser -u "$APP_USER" -- env "XDG_RUNTIME_DIR=/run/user/$APP_UID" "HOME=/home/$APP_USER" "$@"
}

echo "==> Rendering nginx.conf from template with domain: $DOMAIN"
sed "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf.template > nginx/nginx.conf

echo "==> Creating dummy self-signed cert so nginx can start"
mkdir -p "$CERT_PATH" data/certbot/www
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "$CERT_PATH/privkey.pem" \
    -out "$CERT_PATH/fullchain.pem" \
    -subj "/CN=localhost"

echo "==> Handing ownership of certbot data + nginx.conf to $APP_USER"
# certbot writes into data/certbot/conf under its own in-container UID, and
# nginx reads nginx.conf — both need to be owned by the user whose rootless
# Podman is actually running these containers.
chown -R "$APP_USER":"$APP_USER" "$APP_DIR/data" "$APP_DIR/nginx/nginx.conf"

echo "==> Starting nginx with the dummy cert"
run_as_app $COMPOSE up -d --no-deps nginx

echo "==> Removing the dummy cert"
rm -rf "data/certbot/conf/live" "data/certbot/conf/archive" "data/certbot/conf/renewal"

echo "==> Requesting the real certificate from Let's Encrypt"
# --entrypoint overrides the service's renewal-loop entrypoint (in
# compose.prod.yaml) back to plain `certbot` for this one-off call.
run_as_app $COMPOSE run --rm --entrypoint certbot certbot certonly --webroot \
    -w /var/www/certbot --email "$EMAIL" -d "$DOMAIN" \
    --rsa-key-size 2048 --agree-tos --non-interactive

echo "==> Reloading nginx with the real certificate"
run_as_app $COMPOSE exec nginx nginx -s reload

echo "==> Starting the certbot renewal service (checks every 12h, renews automatically)"
run_as_app $COMPOSE up -d --no-deps certbot

echo "==> Done. https://$DOMAIN should now show a trusted certificate."
