#!/usr/bin/env bash
# One-command setup for a fresh Vultr Ubuntu 24.04 server.
#   sudo bash setup_vultr.sh you@example.com
# Before running: put the data and the key on the server (see deploy/RUNBOOK.md):
#   /opt/servaai/data/*.csv   and   /opt/servaai/backend/.env
set -euo pipefail

EMAIL="${1:-}"
REPO="https://github.com/SqualidRat560/servaai.git"
DIR="/opt/servaai"
DOMAIN="servaai.us"

say() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -n "$EMAIL" ] || { echo "Usage: sudo bash setup_vultr.sh you@example.com  (email for the HTTPS certificate)"; exit 1; }

say "Installing Docker, nginx and certbot"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx git curl dnsutils
systemctl enable --now docker nginx

say "Getting the code"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else
  mkdir -p "$DIR"; tmp=$(mktemp -d); git clone "$REPO" "$tmp"; cp -a "$tmp/." "$DIR/"; rm -rf "$tmp"; fi
cd "$DIR"

say "Checking data and key"
[ -f data/monthly_summary.csv ] || { echo "Missing $DIR/data/monthly_summary.csv. Copy the data/ folder first (RUNBOOK step 3)."; exit 1; }
[ -f backend/.env ] || { echo "Missing $DIR/backend/.env. Copy it first (RUNBOOK step 3)."; exit 1; }
chmod 600 backend/.env

say "Building and starting the app (first build takes a few minutes)"
docker compose up -d --build

say "Waiting for the app to answer (it trains the forecast once on first start)"
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then echo "App is up."; break; fi
  sleep 5
  [ "$i" -eq 60 ] && { echo "App did not start. Logs:"; docker compose logs --tail 80; exit 1; }
done
curl -fsS http://127.0.0.1:8000/api/accounts/63816 >/dev/null && echo "Engine answers for account 63816."

say "Configuring nginx"
cp deploy/nginx-servaai.conf /etc/nginx/sites-available/servaai
ln -sf /etc/nginx/sites-available/servaai /etc/nginx/sites-enabled/servaai
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
if command -v ufw >/dev/null && ufw status | grep -q active; then ufw allow 'Nginx Full'; ufw allow OpenSSH; fi

say "Checking DNS before asking for a certificate"
MYIP=$(curl -4 -fsS https://api.ipify.org || true)
DNSIP=$(dig +short A "$DOMAIN" | tail -n1)
echo "This server: $MYIP   $DOMAIN points to: ${DNSIP:-nothing}"
if [ "$MYIP" != "$DNSIP" ]; then
  echo "DNS does not point here yet. The site works on http://$MYIP now."
  echo "Set the A records (RUNBOOK step 2), wait a few minutes, then run:"
  echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN -m $EMAIL --agree-tos --redirect -n"
  exit 0
fi

say "Getting the HTTPS certificate"
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" -m "$EMAIL" --agree-tos --redirect -n
say "Done: https://$DOMAIN"
