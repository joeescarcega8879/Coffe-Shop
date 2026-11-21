# Deploying to a Linux server (Hetzner, Ubuntu/Debian)

Stack: **Caddy** (HTTPS + media) → **gunicorn** (Django) managed by **systemd**.
Static files are served by WhiteNoise; data lives outside the code directory
(`/var/lib/coffeeshop`) so a deploy never touches the database or the photos.

| What | Where |
|---|---|
| Code | `/srv/coffeeshop/app` |
| Virtualenv | `/srv/coffeeshop/venv` |
| Database, media, cache | `/var/lib/coffeeshop/` |
| Environment variables | `/etc/coffeeshop/env` |
| DB backups | `/var/backups/coffeeshop/` |

Prerequisite: a DNS **A record** for your (sub)domain pointing to the server's IP.

## One-time setup (as root / with sudo)

```bash
# 1. Packages (Caddy: https://caddyserver.com/docs/install#debian-ubuntu-raspbian)
sudo apt update && sudo apt install -y python3-venv python3-pip git caddy

# 2. App user and directories
sudo useradd --system --create-home --home-dir /srv/coffeeshop --shell /usr/sbin/nologin coffee
sudo mkdir -p /var/lib/coffeeshop/{media,cache} /etc/coffeeshop
sudo chown -R coffee:coffee /var/lib/coffeeshop
sudo chmod 755 /var/lib/coffeeshop /var/lib/coffeeshop/media   # Caddy must read media

# 3. Code + virtualenv
sudo -u coffee git clone https://github.com/joeescarcega8879/Coffe-Shop.git /srv/coffeeshop/app
sudo -u coffee python3 -m venv /srv/coffeeshop/venv
sudo -u coffee /srv/coffeeshop/venv/bin/pip install -r /srv/coffeeshop/app/requirements.txt

# 4. Environment file (edit the values!)
sudo cp /srv/coffeeshop/app/.env.example /etc/coffeeshop/env
sudo nano /etc/coffeeshop/env          # SECRET_KEY, domain, TIME_ZONE, ...
sudo chown root:coffee /etc/coffeeshop/env && sudo chmod 640 /etc/coffeeshop/env

# 5. Database, static files, demo data, admin user
sudo -u coffee bash -c 'set -a; . /etc/coffeeshop/env; set +a; cd /srv/coffeeshop/app
  /srv/coffeeshop/venv/bin/python manage.py migrate
  /srv/coffeeshop/venv/bin/python manage.py collectstatic --noinput
  /srv/coffeeshop/venv/bin/python manage.py seed_demo --with-orders   # optional demo content
  /srv/coffeeshop/venv/bin/python manage.py createsuperuser'

# 6. Services
sudo cp /srv/coffeeshop/app/deploy/coffeeshop.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now coffeeshop
sudo cp /srv/coffeeshop/app/deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile         # only if you use a different domain
sudo systemctl reload caddy

# 7. Firewall (if ufw is used): allow SSH first!
sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw enable
```

Open `https://your-domain` — the certificate is issued on the first visit.

## Updating

If the update changes `deploy/Caddyfile` (the commit message or `git log` will say so), also run:
`sudo cp /srv/coffeeshop/app/deploy/Caddyfile /etc/caddy/Caddyfile && sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`
(`deploy.sh` does not touch Caddy or systemd files.)

```bash
cd /srv/coffeeshop/app && ./deploy/deploy.sh
```
The script backs up the database (keeps the last 14), pulls, installs, migrates,
collects static files, runs `check --deploy`, restarts and health-checks.

## Keep the demo alive (optional, for a public demo)

The dashboard only lists **today's** orders, so the sample orders would look stale the next day.
A daily systemd timer recreates them dated today (only customers named `Demo - …`; real orders are never touched):

```bash
sudo cp /srv/coffeeshop/app/deploy/coffeeshop-demo-refresh.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now coffeeshop-demo-refresh.timer
systemctl list-timers coffeeshop-demo-refresh.timer      # shows the next run
sudo systemctl start coffeeshop-demo-refresh.service      # run it right now
```
If your `TIME_ZONE` is not `America/Mexico_City`, edit `OnCalendar` in the `.timer` file.
Skip this on a real shop: it is meant for demo data only.

## After it works

- Raise `SECURE_HSTS_SECONDS` to `31536000` in `/etc/coffeeshop/env` and restart.
- In `/admin/` → **Store settings**, set `notify_email` to receive new-order alerts.
- Configure SMTP in the env file if you want real confirmation emails.

## Troubleshooting

```bash
journalctl -u coffeeshop -n 50 --no-pager     # app errors
sudo systemctl status coffeeshop caddy
sudo -u coffee bash -c 'set -a; . /etc/coffeeshop/env; set +a; cd /srv/coffeeshop/app; /srv/coffeeshop/venv/bin/python manage.py check --deploy'
```
- *400 Bad Request* → the domain is missing from `ALLOWED_HOSTS`.
- *403 on forms* → add `https://your-domain` to `CSRF_TRUSTED_ORIGINS`.
- *Photos missing* → check `MEDIA_ROOT` and that `/var/lib/coffeeshop/media` is readable by Caddy.
