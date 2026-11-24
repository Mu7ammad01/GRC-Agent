"""Indexe le corpus réglementaire et les politiques internes dans Chroma.

Chaque passage garde sa provenance (identifiant du texte, niveau dans la pyramide
des normes, article, empreinte SHA-256 du fichier source) : c'est la base de la
citation obligatoire des sources (menace M4) et du contrôle d'ingestion (M5).

Usage : PYTHONPATH=src python -m grc_agent.ingest [--reset]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from .chunking import Chunk, chunk_text, extract_text, file_sha256
from .config import ROOT, settings


def ollama_embedding():
    """Fonction d'embedding Chroma appuyée sur le serveur Ollama local."""
    from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

    return OllamaEmbeddingFunction(url=settings.ollama_url, model_name=settings.embed_model, timeout=300)


def vertex_embedding():
    """Fonction d'embedding Chroma appuyée sur Vertex AI (ni Ollama ni serveur local)."""
    from google import genai

    client = genai.Client(vertexai=True, project=settings.google_project, location=settings.google_location)

    class _VertexEmbedding:
        def name(self):
            return "vertex"

        def __call__(self, input):
            reponse = client.models.embed_content(model=settings.vertex_embed_model, contents=list(input))
            return [e.values for e in reponse.embeddings]

    return _VertexEmbedding()


def choisir_embedding():
    """Choisit la fonction d'embedding selon EMBED_PROVIDER (ollama par défaut)."""
    return vertex_embedding() if settings.embed_provider == "vertex" else ollama_embedding()


def collect_chunks(root: Path = ROOT) -> tuple[list[Chunk], list[str]]:
    """Découpe tous les documents disponibles. Retourne (passages, documents manquants)."""
    sources = yaml.safe_load((root / "corpus" / "sources.yaml").read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    missing: list[str] = []

    for doc in sources["documents"]:
        path = root / "corpus" / "raw" / doc["file"]
        if not path.exists() or path.stat().st_size < 1000:
            missing.append(doc["file"])
            continue
        meta = {
            "source_id": doc["id"],
            "title": doc["title"],
            "norm_level": doc["norm_level"],
            "file": doc["file"],
            "sha256": file_sha256(path),
            "kind": "reglementation",
        }
        chunks += chunk_text(extract_text(path), meta)

    for path in sorted((root / sources["policies_dir"]).glob("*.md")):
        meta = {
            "source_id": f"POL-{path.stem}",
            "title": path.stem.replace("_", " "),
            "norm_level": 5,
            "file": str(path.relative_to(root)),
            "sha256": file_sha256(path),
            "kind": "politique_interne",
        }
        chunks += chunk_text(extract_text(path), meta)

    return chunks, missing


def get_collection(client=None, embedding=None, reset: bool = False):
    import chromadb

    if client is None:
        if settings.chroma_mode == "persistent":
            client = chromadb.PersistentClient(path=settings.chroma_path)
        else:
            client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    if reset:
        try:
            client.delete_collection(settings.chroma_collection)
        except Exception:
            pass
    return client.get_or_create_collection(
        settings.chroma_collection,
        embedding_function=embedding or choisir_embedding(),
        metadata={"hnsw:space": "cosine"},
    )


def index(chunks: list[Chunk], collection, batch: int = 64, progress: bool = False) -> int:
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        collection.upsert(
            ids=[c.id for c in part],
            documents=[c.text for c in part],
            metadatas=[c.metadata for c in part],
        )
        if progress:
            print(f"  {min(i + batch, len(chunks))}/{len(chunks)} passages vectorisés", flush=True)
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="recrée la collection")
    args = parser.parse_args()

    chunks, missing = collect_chunks()
    for name in missing:
        print(f"[manquant] corpus/raw/{name} — voir corpus/sources.yaml")
    try:
        collection = get_collection(reset=args.reset)
    except ValueError as exc:
        raise SystemExit(f"Chroma injoignable sur {settings.chroma_host}:{settings.chroma_port} — lancer `make up`. ({exc})")
    with_article = sum(1 for c in chunks if c.metadata.get("article"))
    print(f"{len(chunks)} passages à vectoriser ({with_article} rattachés à un article), "
          "calcul des embeddings sur processeur…", flush=True)
    n = index(chunks, collection, progress=True)
    print(f"{n} passages indexés dans la collection « {settings.chroma_collection} ».")


if __name__ == "__main__":
    main()
