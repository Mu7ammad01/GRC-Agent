"""Télécharge les textes réglementaires publics listés dans corpus/sources.yaml."""
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    sources = yaml.safe_load((ROOT / "corpus" / "sources.yaml").read_text(encoding="utf-8"))
    for doc in sources["documents"]:
        target = RAW / doc["file"]
        if target.exists():
            print(f"[déjà présent] {doc['file']}")
            continue
        if not doc.get("url"):
            print(f"[à déposer à la main] {doc['file']} — {doc['title']}")
            continue
        try:
            resp = requests.get(doc["url"], timeout=60, headers={"User-Agent": "grc-agent/0.1"})
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[échec] {doc['file']} : {exc.__class__.__name__} — télécharger à la main depuis {doc['url']}")
            continue
        target.write_bytes(resp.content)
        print(f"[téléchargé] {doc['file']} ({len(resp.content) // 1024} Ko)")


if __name__ == "__main__":
    main()
