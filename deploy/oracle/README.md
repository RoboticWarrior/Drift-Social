# Run drift on Oracle Cloud Always Free

This gets the app onto a permanently free VM: an Ampere ARM instance with
2 OCPU / 12 GB RAM and 200 GB of block storage, running the same `Dockerfile`
that Fly.io uses, behind nginx with a Let's Encrypt certificate.

You still have to create the account and the VM yourself — those steps need your
payment-verification details and the Oracle console. Everything after SSH is
scripted.

## 1. Account

Sign up at <https://www.oracle.com/cloud/free/>. A credit card is required for
identity verification; Always Free resources are not billed. Pick your **home
region** carefully — Always Free instances must live there and it can't be
changed later.

## 2. Create the instance

Console → Compute → Instances → **Create instance**.

| Field | Value |
| --- | --- |
| Image | Ubuntu 24.04 (marked "Always Free Eligible") |
| Shape | `VM.Standard.A1.Flex`, **2 OCPU / 12 GB** (the entire free allowance) |
| Boot volume | 47 GB minimum; up to ~100 GB within the 200 GB free total |
| Networking | Assign a **public IPv4 address** |

If you get **"Out of host capacity"**, that region has no free ARM capacity
right now. Retry, try the other availability domain, or wait — it's a common
and temporary condition.

Then reserve the address so it survives a stop/start: Instance details →
Attached VNICs → IPv4 address → **Edit** → reserved public IP.

## 3. Open the cloud firewall

Networking → Virtual Cloud Networks → your VCN → **Security Lists** → default →
Add Ingress Rules:

| Source | Protocol | Destination port |
| --- | --- | --- |
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |
| your IP | TCP | `22` |

This is gate one. Oracle's Ubuntu images *also* ship guest-side iptables rules
that drop everything except SSH — that's gate two, and `bootstrap.sh` opens it.
Skipping either gate gives you a VM that looks healthy over SSH and is
unreachable from a browser.

## 4. Run the bootstrap

```bash
ssh ubuntu@<public-ip>          # 'opc' instead of 'ubuntu' on Oracle Linux images

git clone https://github.com/RoboticWarrior/Drift-Social.git
cd Drift-Social
sudo DOMAIN=drift.example.com EMAIL=you@example.com ./deploy/oracle/bootstrap.sh
```

`DOMAIN` and `EMAIL` are optional. Omit them and you get HTTP on the raw IP, then
add TLS later with `sudo certbot --nginx -d drift.example.com`.

The script installs docker/nginx/certbot, installs the reverse proxy config,
opens 80/443 in the guest firewall, builds the image, waits for `/api/health`,
and — when `DOMAIN` and `EMAIL` are set — requests the certificate.

## 5. DNS

Point an `A` record at the reserved public IP, then either re-run the bootstrap
with `DOMAIN`/`EMAIL` or:

```bash
sudo certbot --nginx -d drift.example.com
```

No domain? `<public-ip>.nip.io` resolves to the IP and works for `certbot` too,
which is handy for a quick HTTPS demo.

## 6. Check it

```bash
curl -sS http://127.0.0.1:8080/api/health     # {"ok": true, "posts": 10}
docker compose ps                             # app: healthy
docker compose logs -f                        # gunicorn access log
sudo reboot                                   # then confirm the site is back
```

The container uses `restart: unless-stopped` and docker is enabled at boot, so a
reboot brings the feed back without intervention.

## 7. Deploying changes

```bash
./deploy/oracle/update.sh
```

Pulls, rebuilds, restarts, and fails loudly if the app doesn't come back
healthy. Your data is in `./data`, outside the image, so it survives rebuilds.

## 8. Backups

Everything stateful is in `./data` (`data/app.db` plus `data/uploads/`):

```bash
tar czf ~/drift-backup-$(date +%F).tar.gz -C ~/Drift-Social data
```

Also worth enabling: Console → Block Storage → Boot Volume → **Backups**
policy, which snapshots the whole disk. Oracle may reclaim an Always Free
instance that stays under 20% CPU, network and memory utilisation for 7 days, so
treat the VM disk as convenient, not sacred.

## Known constraints

- **ARM only.** Both `node:22-alpine` and `python:3.12-slim` are multi-arch, so
  the image builds natively on the A1 shape. Builds take a few minutes on
  2 OCPU; that's normal.
- **No ffmpeg in the image,** so the first boot seeds photos, a GIF and text
  rather than the two video posts. Add `ffmpeg` to the Dockerfile if you want
  those seeded too.
- **One instance.** SQLite needs a single writer; don't scale this out.
- **2 OCPU / 12 GB is the whole free allowance** (halved from 4/24 in June
  2026). Resizing beyond it starts billing.
- Only ports 22, 80 and 443 should be open. The app port stays bound to
  `127.0.0.1`.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| 502 from nginx | Container down or still building: `docker compose ps`, `docker compose logs` |
| Site unreachable, SSH fine | Security List missing 80/443, or guest iptables rules (re-run bootstrap) |
| `413` on posting | `client_max_body_size` lowered in nginx config; keep it at 160m |
| Uploads hang, then 504 | Gunicorn `WEB_TIMEOUT` too low for the connection — raise it in `docker-compose.yml` |
| certbot fails | DNS not pointing at the VM yet, or port 80 blocked |
| "Out of host capacity" at creation | No free ARM capacity in that region/AD; retry later |
