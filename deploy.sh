#!/bin/bash
# deploy.sh — Bootstrap employee-attendance on a fresh Ubuntu/Debian VPS
# Usage: curl -sSL <raw_url>/deploy.sh | bash
# Or:    chmod +x deploy.sh && sudo ./deploy.sh
set -euo pipefail

REPO_URL="https://github.com/Nithin-magzest/emplyeee-attendance.git"
APP_DIR="/opt/employee-attendance"
APP_USER="attendance"

echo "==> Installing system packages"
apt-get update -q
apt-get install -y -q \
    git curl ca-certificates gnupg \
    docker.io docker-compose-plugin \
    ufw fail2ban unattended-upgrades openssl

systemctl enable --now docker

echo "==> Hardening: firewall (ufw)"
# No 'ufw --force reset' here — this script is meant to be safely re-run (see
# the .env placeholder check below), and a reset would silently wipe any
# custom rules an operator added between runs. allow/limit/default are all
# idempotent on their own, so just (re-)apply the baseline.
ufw default deny incoming
ufw default allow outgoing
ufw limit 22/tcp    # rate-limited SSH — slows down brute-force attempts
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Hardening: fail2ban (SSH brute-force protection)"
systemctl enable --now fail2ban

echo "==> Hardening: automatic OS security patches"
dpkg-reconfigure -f noninteractive unattended-upgrades || true
systemctl enable --now unattended-upgrades

echo "==> Hardening: SSH key-only auth"
# Ubuntu cloud images load /etc/ssh/sshd_config.d/*.conf (e.g. cloud-init's
# 50-cloud-init.conf, which sets PasswordAuthentication yes) via an Include
# near the top of sshd_config — and sshd uses the FIRST value it sees for
# each keyword, so editing only the main file below can silently lose to
# that drop-in. Write our own drop-in that sorts before it (00- prefix) so
# it wins, in addition to editing the main file for clarity/older OpenSSH.
mkdir -p /etc/ssh/sshd_config.d
echo "PasswordAuthentication no" > /etc/ssh/sshd_config.d/00-attendance-hardening.conf
if grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
    sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
else
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
fi
systemctl reload sshd || systemctl reload ssh || true
if command -v sshd >/dev/null && sshd -T 2>/dev/null | grep -qi "^passwordauthentication yes"; then
    echo "    WARNING: PasswordAuthentication is still enabled after hardening —"
    echo "    check /etc/ssh/sshd_config.d/ for a conflicting drop-in that loads"
    echo "    before 00-attendance-hardening.conf."
fi

echo "==> Creating app user and directory"
id -u "$APP_USER" &>/dev/null || useradd -r -s /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"
chown "$APP_USER":"$APP_USER" "$APP_DIR"
usermod -aG docker "$APP_USER"

echo "==> Cloning / pulling repository"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull origin master
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Setting up .env file"
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" <<EOF
# Production: point DB_HOST at the RDS endpoint from 'terraform output rds_endpoint'.
# DB_USER / DB_PASS must match what you set for db_username / db_password in terraform.tfvars.
DB_HOST=REPLACE_WITH_RDS_ENDPOINT
DB_USER=attendance_admin
DB_PASS=REPLACE_WITH_RDS_PASSWORD
DB_NAME=employee_attendance
SECRET_KEY=$(openssl rand -hex 32)
# Encrypts PII (Aadhar/PAN/bank account) at rest — without this it's stored in plaintext.
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
APP_ENV=production
# Set to your real domain, e.g. https://yourdomain.com
ALLOWED_ORIGINS=REPLACE_WITH_DOMAIN
EOF
    echo "    .env created — fill in the RDS/domain placeholders at $APP_DIR/.env, then re-run this script"
fi

cd "$APP_DIR"
if grep -q "REPLACE_WITH" .env; then
    echo ""
    echo "====================================================="
    echo "  .env still has REPLACE_WITH_* placeholders."
    echo "  Edit $APP_DIR/.env, then re-run deploy.sh to start the app."
    echo "====================================================="
    exit 0
fi

echo "==> Generating internal app<->nginx cert (if missing)"
# docker-compose.yml bind-mounts ./cert.pem and ./key.pem from the host; if
# they don't exist yet, Docker creates empty files for the mount instead of
# failing, which breaks gunicorn's SSL startup. This is only used for the
# nginx->app hop internally (nginx terminates the real cert from certbot).
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
        -keyout key.pem -out cert.pem -subj "/CN=localhost"
fi

echo "==> Building and starting app + redis (production stack, RDS-backed)"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$COMPOSE build app
$COMPOSE up -d --no-deps app redis
# nginx/certbot are intentionally not started here — nginx.conf doesn't
# exist yet (it's rendered from nginx/nginx.conf.template by
# init-letsencrypt.sh, which also brings up nginx + certbot).

echo "==> Scheduling daily nginx reload (so renewed certs take effect)"
# `crontab -l` fails (no crontab yet) on a fresh box — `|| true` keeps that
# from tripping `set -e` and aborting the script before it reaches the end.
( crontab -l 2>/dev/null | grep -v "nginx -s reload" || true; \
  echo "30 3 * * * cd $APP_DIR && $COMPOSE exec -T nginx nginx -s reload >/dev/null 2>&1" ) | crontab -

echo ""
echo "====================================================="
echo "  App + Redis running. Next: run"
echo "    ./init-letsencrypt.sh <domain> <email>"
echo "  once to render nginx.conf, get a trusted HTTPS cert, and start nginx."
echo "====================================================="
echo "  Useful commands:"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f app"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml restart app"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml down"
echo "====================================================="
