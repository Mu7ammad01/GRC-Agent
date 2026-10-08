"""Tests du découpage et de l'indexation (Chroma local, embedding de test, sans Ollama)."""
import hashlib
import shutil
from pathlib import Path

import pytest

from grc_agent.chunking import chunk_text, extract_text
from grc_agent.ingest import collect_chunks, index

ROOT = Path(__file__).resolve().parents[1]


class FakeEmbedding:
    """Embedding déterministe (sac de mots haché) pour tester sans modèle."""

    def __call__(self, input):
        vectors = []
        for text in input:
            v = [0.0] * 64
            for word in text.lower().split():
                v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
            vectors.append(v)
        return vectors

    def name(self):
        return "fake-test"

    def embed_query(self, input):
        return self(input)


def test_decoupage_garde_le_numero_d_article():
    text = "Préambule.\n\nArticle 28\nPrincipes généraux.\n\nLe registre est tenu à jour.\n\nArticle 30\nClauses contractuelles."
    chunks = chunk_text(text, {"source_id": "X"}, max_chars=200, overlap=0)
    articles = [c.metadata.get("article") for c in chunks]
    assert "Art. 28" in articles and "Art. 30" in articles
    assert any("registre" in c.text and c.metadata.get("article") == "Art. 28" for c in chunks)


def test_decoupage_respecte_la_taille_max():
    text = "\n\n".join(["mot " * 100] * 20)
    chunks = chunk_text(text, {"source_id": "X"}, max_chars=500, overlap=50)
    assert chunks and all(len(c.text) <= 500 + 60 for c in chunks)


def test_extraction_html(tmp_path):
    html = tmp_path / "t.html"
    html.write_text("<html><script>x()</script><body><p>Article 5</p><p>Gouvernance</p></body></html>", encoding="utf-8")
    text = extract_text(html)
    assert "Gouvernance" in text and "x()" not in text


def test_politiques_indexees_avec_provenance(tmp_path):
    chromadb = pytest.importorskip("chromadb")
    # Copie minimale du dépôt : sources.yaml + politiques, sans corpus téléchargé
    (tmp_path / "corpus").mkdir()
    shutil.copy(ROOT / "corpus" / "sources.yaml", tmp_path / "corpus" / "sources.yaml")
    shutil.copytree(ROOT / "data" / "policies", tmp_path / "data" / "policies")

    chunks, missing = collect_chunks(tmp_path)
    assert len(missing) == 5            # aucun texte téléchargé dans ce test
    assert len(chunks) >= 3
    assert all(c.metadata["norm_level"] == 5 and len(c.metadata["sha256"]) == 64 for c in chunks)

    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection("test", embedding_function=FakeEmbedding())
    assert index(chunks, col) == len(chunks)
    assert col.count() == len(chunks)

    res = col.query(query_texts=["registre d'information des prestataires TIC"], n_results=1)
    assert "prestataires" in res["metadatas"][0][0]["source_id"]
