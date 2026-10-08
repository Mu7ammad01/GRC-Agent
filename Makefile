-include .env
export

.PHONY: up down reset models seed corpus ingest test psql

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
