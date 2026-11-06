#!/usr/bin/env bash
# Campagne J5 : 3 passages par menace, base reinitialisee avant chacun.
# Usage : bash scripts/j5_passages.sh [fournisseur] [modele] [menaces...]
export MSYS_NO_PATHCONV=1
export PYTHONUTF8=1
set -a; [ -f .env ] && . ./.env; set +a
fournisseur=${1:-google_genai}
modele=${2:-gemini-3.8-flash}
shift $(( $# < 2 ? $# : 2 ))
menaces="$@"
[ -z "$menaces" ] && menaces="m2 m5 m6 m1 m3 m4 m7 m8"
for menace in $menaces; do
  for i in 1 2 3; do
    echo "=== $menace passage $i $(date +%H:%M) ==="
    docker compose exec -T postgres psql -U grc -d grc -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    docker compose exec -T postgres psql -U grc -d grc -q -f /docker-entrypoint-initdb.d/01_schema.sql
    docker compose exec -T postgres psql -U grc -d grc -q -f /docker-entrypoint-initdb.d/02_seed.sql
    PYTHONPATH=src python -m grc_agent.cli --scenario $menace --provider $fournisseur --model $modele
  done
done