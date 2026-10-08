"""Télécharge les textes réglementaires publics listés dans corpus/sources.yaml.

EUR-Lex bloque parfois les téléchargements automatisés et renvoie une page vide
ou une page de vérification. Le script vérifie donc que le fichier reçu est un
vrai document ; sinon il indique le lien à ouvrir dans un navigateur.
"""
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
MIN_BYTES = 20_000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def looks_valid(target: Path, content: bytes) -> bool:
    if len(content) < MIN_BYTES:
        return False
    if target.suffix.lower() == ".pdf":
        return content[:5] == b"%PDF-"
    return True


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    sources = yaml.safe_load((ROOT / "corpus" / "sources.yaml").read_text(encoding="utf-8"))
    for doc in sources["documents"]:
        target = RAW / doc["file"]
        if target.exists() and target.stat().st_size >= MIN_BYTES:
            print(f"[déjà présent] {doc['file']}")
            continue
        if not doc.get("url"):
            print(f"[à déposer à la main] corpus/raw/{doc['file']} — {doc['title']}")
            continue
        try:
            resp = requests.get(doc["url"], timeout=90, headers=HEADERS)
            resp.raise_for_status()
            content = resp.content
        except requests.RequestException as exc:
            content = b""
            print(f"[erreur réseau] {doc['file']} : {exc.__class__.__name__}")
        if looks_valid(target, content):
            target.write_bytes(content)
            print(f"[téléchargé] {doc['file']} ({len(content) // 1024} Ko)")
        else:
            target.unlink(missing_ok=True)
            print(
                f"[bloqué] {doc['file']} : réponse vide ou invalide ({len(content)} octets).\n"
                f"          Ouvrir {doc['url']} dans un navigateur et enregistrer le PDF sous corpus/raw/{doc['file']}"
            )


if __name__ == "__main__":
    main()
