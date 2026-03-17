#!/bin/bash
# Budget Master — Production Deployment Script
# Usage: ./deploy.sh [init|update|ssl|logs|seed]
set -euo pipefail

VPS_USER="root"
VPS_HOST="72.62.21.162"
APP_DIR="/opt/budget-master"
REPO="https://github.com/joshkabs95/budget-master.git"
DOMAIN="srv1404625.hstgr.cloud"
CERTBOT_EMAIL="admin@${DOMAIN}"

# ── Colors ────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

CMD="${1:-init}"

case "$CMD" in

# ── INIT — first-time deployment ──────────────────────────
init)
  info "Initial deployment to ${VPS_HOST}..."

  ssh "${VPS_USER}@${VPS_HOST}" bash <<REMOTE
set -euo pipefail

# Install Docker if needed
if ! command -v docker &>/dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

# Install Docker Compose plugin if needed
if ! docker compose version &>/dev/null; then
  apt-get update -qq && apt-get install -y docker-compose-plugin
fi

# Clone repo
if [ -d "${APP_DIR}" ]; then
  echo "Directory ${APP_DIR} already exists — pulling latest..."
  cd "${APP_DIR}" && git pull
else
  git clone "${REPO}" "${APP_DIR}"
fi

cd "${APP_DIR}"

# Create .env from example if missing
if [ ! -f .env ]; then
  cp .env.example .env
  # Generate a random SECRET_KEY
  SECRET=\$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  DB_PASS=\$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  GRAFANA_PASS=\$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
  sed -i "s/change-me-in-production-use-50-random-chars/\${SECRET}/" .env
  sed -i "s/change-me-strong-password/\${DB_PASS}/" .env
  sed -i "s/change-me-grafana-password/\${GRAFANA_PASS}/" .env
  echo ".env created with random secrets"
fi

# Start with HTTP-only config first (before SSL)
cp nginx/conf.d/default.http.conf nginx/conf.d/default.conf

# Build & start services (without certbot initially)
docker compose up -d --build db backend nginx

echo "Waiting for services to be ready..."
sleep 10

docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py createsuperuser --noinput \
  --username admin --email admin@${DOMAIN} 2>/dev/null || true

echo "Services up. Requesting SSL certificate..."
REMOTE

  # Get SSL cert
  ssh "${VPS_USER}@${VPS_HOST}" "
    cd ${APP_DIR}
    docker compose run --rm certbot certonly \
      --webroot -w /var/www/certbot \
      --email ${CERTBOT_EMAIL} \
      --agree-tos --no-eff-email \
      -d ${DOMAIN} || echo 'SSL skipped (DNS may not be configured yet)'
  "

  # Switch to full HTTPS config
  ssh "${VPS_USER}@${VPS_HOST}" "
    cd ${APP_DIR}
    # Download recommended nginx SSL params from certbot if cert was issued
    if [ -d /etc/letsencrypt/live/${DOMAIN} ] || \
       docker compose exec certbot test -d /etc/letsencrypt/live/${DOMAIN} 2>/dev/null; then
      cp nginx/conf.d/default.conf nginx/conf.d/default.conf
      docker compose up -d --build nginx certbot prometheus postgres-exporter nginx-exporter grafana
    else
      warning 'SSL cert not available — staying on HTTP. Run: ./deploy.sh ssl'
      docker compose up -d prometheus postgres-exporter nginx-exporter grafana
    fi
  "

  info "Deployment done! Access: http://${VPS_HOST}"
  ;;

# ── UPDATE — pull & redeploy ───────────────────────────────
update)
  info "Updating ${VPS_HOST}..."
  ssh "${VPS_USER}@${VPS_HOST}" "
    cd ${APP_DIR}
    git pull
    docker compose up -d --build backend nginx
    docker compose exec backend python manage.py migrate --noinput
  "
  info "Update complete."
  ;;

# ── SSL — issue/renew certificate ─────────────────────────
ssl)
  info "Issuing SSL certificate for ${DOMAIN}..."
  ssh "${VPS_USER}@${VPS_HOST}" "
    cd ${APP_DIR}
    docker compose run --rm certbot certonly \
      --webroot -w /var/www/certbot \
      --email ${CERTBOT_EMAIL} \
      --agree-tos --no-eff-email \
      -d ${DOMAIN}

    # Switch to HTTPS nginx config
    cp nginx/conf.d/default.conf nginx/conf.d/active.conf
    docker compose restart nginx
  "
  info "SSL done. Site should be accessible at https://${DOMAIN}"
  ;;

# ── SEED — load demo data ──────────────────────────────────
seed)
  info "Seeding demo data..."
  ssh "${VPS_USER}@${VPS_HOST}" "
    cd ${APP_DIR}
    docker compose exec backend python manage.py seed_data
  "
  ;;

# ── LOGS — follow logs ─────────────────────────────────────
logs)
  ssh "${VPS_USER}@${VPS_HOST}" "cd ${APP_DIR} && docker compose logs -f --tail=100"
  ;;

*)
  echo "Usage: $0 [init|update|ssl|seed|logs]"
  exit 1
  ;;
esac
