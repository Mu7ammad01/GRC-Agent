#!/usr/bin/env bash
# Déploie l'app sur Cloud Run (public, pour la démo CV). Prérequis : voir le cahier de déploiement.
set -e
PROJET=${GOOGLE_CLOUD_PROJECT:-hackaton-prep-473512}
REGION=${REGION:-europe-west1}
SA=sa-api-bel@${PROJET}.iam.gserviceaccount.com
gcloud run deploy grc-agent \
  --source . \
  --project "$PROJET" \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --memory 1Gi --cpu 1 --timeout 600 --max-instances 3 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJET},GOOGLE_CLOUD_LOCATION=global" \
  --set-secrets "DATABASE_URL=grc-db-url:latest"
