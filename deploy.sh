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
# DB_HOST: use 'db' for the bundled MySQL container (quick-start / no RDS).
# For AWS RDS: set to the RDS endpoint from 'terraform output rds_endpoint'
# and change COMPOSE in this script to use docker-compose.prod.yml overlay.
DB_HOST=db
DB_USER=attendance_admin
DB_PASS=REPLACE_WITH_STRONG_PASSWORD
DB_NAME=employee_attendance
SECRET_KEY=$(openssl rand -hex 32)
# Encrypts PII (Aadhar/PAN/bank account) at rest — without this it's stored in plaintext.
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
APP_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=REPLACE_WITH_ADMIN_PASSWORD
# Public URL for password-reset and offer-letter email links.
# Use https://yourdomain.com when you have a domain; use http://YOUR_SERVER_IP for now.
APP_URL=REPLACE_WITH_URL
# CORS: set to your domain when live, e.g. https://yourdomain.com
ALLOWED_ORIGINS=*
REDIS_URL=redis://redis:6379/0
EOF
    echo "    .env created — fill in the REPLACE_WITH_* values at $APP_DIR/.env, then re-run this script"
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

echo "==> Rendering nginx.conf (HTTP-only for IP access; will be replaced by init-letsencrypt.sh once you have a domain)"
if [ ! -f "$APP_DIR/nginx/nginx.conf" ]; then
    cat > "$APP_DIR/nginx/nginx.conf" <<'NGINXEOF'
upstream app {
    server app:5000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias /app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass         https://app;
        proxy_ssl_verify   off;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
NGINXEOF
    echo "    nginx.conf written (HTTP-only). Run ./init-letsencrypt.sh <domain> <email> later to add HTTPS."
fi

echo "==> Building and starting full stack (app + MySQL + Redis + nginx)"
COMPOSE="docker compose"
$COMPOSE build app
$COMPOSE up -d
# When you add a domain and want HTTPS + RDS, switch to:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps app nginx certbot redis
# (after editing DB_HOST in .env to point at your RDS endpoint)

echo "==> Scheduling daily nginx reload (so renewed certs take effect)"
# `crontab -l` fails (no crontab yet) on a fresh box — `|| true` keeps that
# from tripping `set -e` and aborting the script before it reaches the end.
( crontab -l 2>/dev/null | grep -v "nginx -s reload" || true; \
  echo "30 3 * * * cd $APP_DIR && $COMPOSE exec -T nginx nginx -s reload >/dev/null 2>&1" ) | crontab -

echo ""
echo "====================================================="
echo "  Stack is up! Access the app at:"
echo "    http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo YOUR_SERVER_IP)"
echo ""
echo "  NEXT STEPS:"
echo "  1. Complete setup at http://YOUR_IP/setup"
echo "  2. When you add a domain, run:"
echo "       ./init-letsencrypt.sh yourdomain.com your@email.com"
echo "     This switches nginx to HTTPS + gets a trusted cert."
echo "====================================================="
echo "  Useful commands:"
echo "    docker compose logs -f app"
echo "    docker compose restart app"
echo "    docker compose down"
echo "====================================================="
