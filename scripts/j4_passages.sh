#!/usr/bin/env bash
# Passages J4 : 3 scénarios × 3 passages pour un modèle donné en argument
export MSYS_NO_PATHCONV=1
modele=$1
for scenario in uc1 uc2 uc2-ecarts; do
  for i in 1 2 3; do
        echo "=== $modele $scenario passage $i $(date +%H:%M) ==="
        docker compose exec -T postgres psql -U grc -d grc -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        docker compose exec -T postgres psql -U grc -d grc -q -f /docker-entrypoint-initdb.d/01_schema.sql
        docker compose exec -T postgres psql -U grc -d grc -q -f /docker-entrypoint-initdb.d/02_seed.sql
        PYTHONPATH=src python -m grc_agent.cli --scenario $scenario --provider ollama --model $modele
      done
  done
