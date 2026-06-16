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
    docker.io docker-compose-plugin

systemctl enable --now docker

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
DB_HOST=db
DB_USER=attendance_user
DB_PASS=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)
DB_NAME=employee_attendance
SECRET_KEY=$(openssl rand -hex 32)
EOF
    echo "    .env created — review it at $APP_DIR/.env before starting"
fi

echo "==> Building and starting containers"
cd "$APP_DIR"
docker compose build
docker compose up -d

echo ""
echo "====================================================="
echo "  Deploy complete!  App running at http://$(hostname -I | awk '{print $1}')"
echo "====================================================="
echo "  Useful commands:"
echo "    docker compose logs -f app    # live app logs"
echo "    docker compose restart app    # restart app"
echo "    docker compose down           # stop everything"
echo "====================================================="
