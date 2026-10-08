# GRC-Agent

Agent IA d'assistance à la **gouvernance, gestion des risques et conformité (GRC)** pour une banque luxembourgeoise fictive, la *Banque Exemple Luxembourg (BEL)*.

L'agent aide la 1re et la 2e ligne de défense à identifier, évaluer, relier et suivre les risques, obligations réglementaires et contrôles. **Il ne décide jamais à la place d'un humain habilité** : chaque action passe par une couche d'autorité explicite (niveaux N0 à N3) et toute modification du registre exige une validation humaine nominative.

> Projet de fin d'études — Mastère Spécialisé Cybersécurité & Smart Systems, CY Tech.
> Toutes les données du dépôt sont **fictives**. Aucune donnée bancaire réelle n'est utilisée.

## Cas d'usage (MVP)

| # | Cas d'usage | Niveau max. |
|---|---|---|
| UC1 | Assistant RCSA : proposer risques, contrôles et cotations à partir d'un processus | N2 |
| UC2 | Cartographie réglementaire : relier obligations (DORA, CSSF) et contrôles | N2 |
| UC3 | Analyse d'écarts d'une politique interne | N1 |
| UC4 | Suivi des incidents et KRI, alertes vs appétit pour le risque | N2 |
| UC5 | Projet de rapport trimestriel risques et conformité | N1 |

**Niveaux d'autorité** : N0 lire · N1 proposer (brouillon) · N2 écrire après validation humaine · N3 interdit (accepter un risque, modifier l'appétit, clôturer un incident, notifier la CSSF, supprimer une trace).

## Architecture

```
Utilisateurs (1re/2e ligne, CRO, CCO) ─► Interface (Streamlit)
        ─► Garde-fous d'entrée/sortie (Presidio, Llama Guard)
        ─► Orchestrateur (LangGraph + LLM local via Ollama)
        ─► Couche d'autorité (Open Policy Agent) ──► Validation humaine (N2)
        ─► Outils GRC : RAG réglementaire (Chroma) · Base GRC (PostgreSQL)
                        Incidents & KRI · Générateur de rapports
Tout est tracé dans un journal d'audit signé (Langfuse, alertes Wazuh).
```

Détails : [`docs/J1_Cadrage_Agent_GRC_Banque.pdf`](docs/J1_Cadrage_Agent_GRC_Banque.pdf).

## Arborescence

```
grc-agent/
├── docker-compose.yml     # PostgreSQL, Chroma, Ollama
├── Makefile               # commandes courantes
├── db/
│   ├── 01_schema.sql      # schéma de la base GRC
│   └── 02_seed.sql        # données fictives (généré)
├── data/
│   ├── seed/              # mêmes données en CSV (généré)
│   └── policies/          # politiques internes fictives de la BEL
├── corpus/
│   ├── sources.yaml       # textes réglementaires à indexer
│   └── raw/               # textes téléchargés (non versionné)
├── scripts/
│   ├── generate_seed.py   # génère db/02_seed.sql et data/seed/*.csv
│   └── download_corpus.py # télécharge les textes publics
├── src/grc_agent/
│   ├── config.py
│   ├── chunking.py        # découpage des documents
│   └── ingest.py          # indexation dans Chroma (embeddings Ollama)
├── policies/              # règles OPA de la couche d'autorité (semaine 2)
├── tests/
└── docs/
```

## Démarrage rapide

Prérequis : Docker et Docker Compose, Python 3.11+, environ 8 Go de RAM libre pour le modèle local.

```bash
cp .env.example .env
make up            # lance PostgreSQL (schéma + données), Chroma et Ollama
make models        # télécharge le LLM et le modèle d'embeddings dans Ollama
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make corpus        # télécharge les textes publics (DORA…)
make ingest        # indexe textes et politiques dans Chroma
make test
```

La base est accessible sur `localhost:5432` (identifiants dans `.env`). Exemple :

```sql
-- risques dont le risque résiduel dépasse l'appétit
SELECT * FROM v_risks_over_appetite;
```

## Feuille de route (3 semaines)

| Jour | Objectif | Statut |
|---|---|---|
| J1 | Cadrage, architecture, modèle de menace | fait |
| J2 | Environnement, base GRC, données fictives, corpus indexé | fait |
| J3 | Premier agent LangGraph (UC1, UC2), sans protection | à faire |
| J4-J5 | Tests offensifs de référence (menaces M1 à M8) | à faire |
| S2 | Couche d'autorité OPA, garde-fous, journalisation, re-tests | à faire |
| S3 | Dossier de gouvernance (AI Act, DORA, ISO/IEC 42001), rapport, démo | à faire |

## Avertissements

- `data/policies/politique_gestion_incidents.md` contient **volontairement** une injection de prompt indirecte, utilisée pour les tests de la menace M2. Voir [`tests/README.md`](tests/README.md).
- Les supports de formation utilisés pour le cadrage ne sont pas versionnés (droits d'auteur).
