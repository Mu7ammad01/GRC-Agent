"""Extraction de texte et découpage des documents en passages indexables."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

ARTICLE_RE = re.compile(r"^\s*(Article|Art\.)\s+(\d+[a-z]?)\b", re.IGNORECASE)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        key = f"{self.metadata.get('source_id')}|{self.metadata.get('position')}|{self.text}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def extract_text(path: Path) -> str:
    """Texte brut d'un fichier .md, .txt, .html ou .pdf."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text("\n")
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raise ValueError(f"Format non pris en charge : {path.name}")


def _paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n")
    parts = re.split(r"\n\s*\n", text)
    return [re.sub(r"[ \t]+", " ", p).strip() for p in parts if p.strip()]


def chunk_text(text: str, base_metadata: dict, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    """Regroupe les paragraphes jusqu'à max_chars, avec chevauchement.

    Le numéro d'article en cours (« Article 28 ») est conservé en métadonnée,
    pour que l'agent puisse citer précisément sa source.
    """
    chunks: list[Chunk] = []
    buffer = ""
    article = None
    buffer_article = None

    def flush():
        nonlocal buffer, buffer_article
        if buffer.strip():
            meta = dict(base_metadata, position=len(chunks))
            if buffer_article:
                meta["article"] = buffer_article
            chunks.append(Chunk(buffer.strip(), meta))
        tail = buffer[-overlap:] if overlap else ""
        buffer = tail
        buffer_article = article

    for para in _paragraphs(text):
        m = ARTICLE_RE.match(para)
        if m:
            flush()
            buffer = ""
            article = f"Art. {m.group(2)}"
            buffer_article = article
        if len(buffer) + len(para) + 1 > max_chars and buffer.strip():
            flush()
        while len(para) > max_chars:
            buffer += para[:max_chars]
            para = para[max_chars:]
            flush()
        buffer += ("\n" if buffer else "") + para
        if buffer_article is None:
            buffer_article = article
    flush()
    return chunks


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
