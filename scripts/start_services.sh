#!/usr/bin/env bash
# Démarre PostgreSQL, Chroma et Ollama, puis télécharge les modèles manquants.
# Appelé automatiquement au démarrage du Codespace ; peut aussi être lancé à la main.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env
set -a; . ./.env; set +a

echo "Attente du démon Docker…"
for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker info >/dev/null 2>&1 || { echo "Docker indisponible" >&2; exit 1; }

docker compose up -d

echo "Attente d'Ollama…"
for _ in $(seq 1 60); do docker compose exec -T ollama ollama list >/dev/null 2>&1 && break; sleep 2; done

for model in "${LLM_MODEL:-qwen2.5:7b}" "${EMBED_MODEL:-nomic-embed-text}"; do
  if [ "${LLM_PROVIDER:-ollama}" != "ollama" ] && [ "$model" = "${LLM_MODEL:-}" ]; then
    continue   # LLM cloud : seul le modèle d'embeddings est nécessaire en local
  fi
  if docker compose exec -T ollama ollama list | awk 'NR>1 {print $1}' | grep -qx -e "$model" -e "$model:latest"; then
    echo "Modèle présent : $model"
  else
    echo "Téléchargement du modèle : $model"
    docker compose exec -T ollama ollama pull "$model"
  fi
done

df -h / | awk 'NR==2 {print "Disque : " $4 " libres (" $5 " utilisés)"}'
echo "Services prêts. Si le corpus n'est pas indexé : make ingest"
