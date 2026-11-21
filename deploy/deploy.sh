#!/usr/bin/env bash
# Update the running site. Run on the server as a user with sudo:  ./deploy/deploy.sh
#   1. backs up the database   2. pulls the code   3. installs deps
#   4. migrates + collects static files   5. restarts   6. health check
set -euo pipefail

APP=/srv/coffeeshop/app
VENV=/srv/coffeeshop/venv
ENV_FILE=/etc/coffeeshop/env
BACKUPS=/var/backups/coffeeshop
KEEP=14

# Run a command as the app user with the production environment loaded
as_app() { sudo -u coffee bash -c "set -a; . '$ENV_FILE'; set +a; cd '$APP'; $*"; }

echo "==> Backing up database"
sudo mkdir -p "$BACKUPS" && sudo chown coffee:coffee "$BACKUPS"
as_app "$VENV/bin/python - <<'PY'
import os, sqlite3, time
src = sqlite3.connect(os.environ['DB_PATH'])
dst = sqlite3.connect('$BACKUPS/db-' + time.strftime('%Y%m%d-%H%M%S') + '.sqlite3')
src.backup(dst); dst.close(); src.close()
PY"
as_app "ls -1t '$BACKUPS'/db-*.sqlite3 | tail -n +$((KEEP + 1)) | xargs -r rm --"

echo "==> Pulling code"
as_app "git pull --ff-only"

echo "==> Installing dependencies"
as_app "'$VENV/bin/pip' install -q -r requirements.txt"

echo "==> Migrating and collecting static files"
as_app "'$VENV/bin/python' manage.py migrate --noinput"
as_app "'$VENV/bin/python' manage.py collectstatic --noinput --verbosity 0"
as_app "'$VENV/bin/python' manage.py check --deploy"

echo "==> Restarting"
sudo systemctl restart coffeeshop
sleep 2

echo "==> Health check"
HOST=$(as_app 'echo "${ALLOWED_HOSTS%%,*}"')
curl -fsS -o /dev/null -H "Host: $HOST" -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/ \
  && echo "OK: site is responding" \
  || { echo "FAILED: check 'journalctl -u coffeeshop -n 50'"; exit 1; }
