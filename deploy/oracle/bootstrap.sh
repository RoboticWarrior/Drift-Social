#!/usr/bin/env bash
# bootstrap.sh — turn a fresh Ubuntu 22.04/24.04 VM (Oracle Cloud Always Free)
# into a host for drift: docker + docker compose, nginx reverse proxy, open
# firewall ports, and optionally a Let's Encrypt certificate.
#
# Usage (on the VM, after cloning the repo):
#   sudo DOMAIN=drift.example.com EMAIL=you@example.com ./deploy/oracle/bootstrap.sh
#
# DOMAIN/EMAIL are optional. Without them everything is set up for plain HTTP on
# the VM's public IP, and you can add TLS later with:
#   sudo certbot --nginx -d drift.example.com
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REPO_URL="${REPO_URL:-https://github.com/RoboticWarrior/Drift-Social.git}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"

if [ "$(id -u)" -ne 0 ]; then
  echo "bootstrap.sh must run as root (use sudo)." >&2
  exit 1
fi

echo "==> installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold \
  ca-certificates curl git nginx certbot python3-certbot-nginx \
  iptables netfilter-persistent

echo "==> installing docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
if ! docker compose version >/dev/null 2>&1; then
  echo "==> installing the docker compose plugin"
  apt-get install -y docker-compose-plugin
fi

# Oracle's Ubuntu images ship iptables rules that drop everything but SSH, and
# the cloud-side Security List is a second, independent gate. Both must allow
# HTTP/HTTPS or the site is unreachable while looking perfectly healthy locally.
echo "==> opening ports 80 and 443 in the guest firewall"
open_port() {
  local port="$1"
  if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
  fi
}
open_port 80
open_port 443
if command -v netfilter-persistent >/dev/null 2>&1; then
  netfilter-persistent save
else
  mkdir -p /etc/iptables
  iptables-save >/etc/iptables/rules.v4
fi

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "==> cloning $REPO_URL into $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi

echo "==> configuring nginx"
install -m 0644 "$REPO_DIR/deploy/oracle/nginx/drift.conf" /etc/nginx/sites-available/drift.conf
ln -sf /etc/nginx/sites-available/drift.conf /etc/nginx/sites-enabled/drift.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> building and starting the app (first build takes a few minutes)"
cd "$REPO_DIR"
mkdir -p data
docker compose up -d --build

echo "==> waiting for the app to answer on 127.0.0.1:8080"
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 5 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
    echo "    app is healthy"
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "    app did not become healthy; check: docker compose logs --tail=100" >&2
    exit 1
  fi
  sleep 5
done

if [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  echo "==> requesting a Let's Encrypt certificate for $DOMAIN"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
fi

PUBLIC_IP="$(curl -fsS --max-time 5 https://ifconfig.me || echo '<public-ip>')"
echo
echo "done."
if [ -n "$DOMAIN" ]; then
  echo "  https://$DOMAIN"
else
  echo "  http://$PUBLIC_IP  (add TLS: sudo certbot --nginx -d <domain>)"
fi
echo "  logs:    docker compose logs -f"
echo "  redeploy: ./deploy/oracle/update.sh"
