-include .env
export

.PHONY: services up down reset models seed corpus ingest test psql ask demo-uc1 demo-uc2 reset-db

services:      ## Lance les services et télécharge les modèles manquants (auto dans Codespaces)
	bash scripts/start_services.sh

up:            ## Lance PostgreSQL, Chroma et Ollama
	docker compose up -d

down:          ## Arrête les services
	docker compose down

reset:         ## Supprime les volumes (base rechargée au prochain up)
	docker compose down -v

models:        ## Télécharge le LLM et le modèle d'embeddings
	docker compose exec ollama ollama pull $(LLM_MODEL)
	docker compose exec ollama ollama pull $(EMBED_MODEL)

seed:          ## Régénère db/02_seed.sql et data/seed/*.csv
	python scripts/generate_seed.py

corpus:        ## Télécharge les textes réglementaires publics
	python scripts/download_corpus.py

ingest:        ## Indexe le corpus et les politiques dans Chroma
	PYTHONPATH=src python -m grc_agent.ingest

test:          ## Lance les tests
	PYTHONPATH=src pytest -q

psql:          ## Ouvre une console SQL sur la base GRC
	docker compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

ask:           ## Pose une question : make ask Q="..." U=u.dupont
	PYTHONPATH=src python -m grc_agent.cli --user $(or $(U),u.dupont) "$(Q)"

demo-uc1:      ## Scénario UC1 (RCSA)
	PYTHONPATH=src python -m grc_agent.cli --scenario uc1

demo-uc2:      ## Scénario UC2 (cartographie DORA art. 30)
	PYTHONPATH=src python -m grc_agent.cli --scenario uc2

reset-db:      ## Recharge la base GRC à son état initial (efface les écritures de l'agent)
	docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -q -f /docker-entrypoint-initdb.d/01_schema.sql
	docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -q -f /docker-entrypoint-initdb.d/02_seed.sql
