"""Interface en ligne de commande de GRC-Agent.

Exemples :
  PYTHONPATH=src python -m grc_agent.cli --user u.dupont "Quels risques TIC sont hors appétit ?"
  PYTHONPATH=src python -m grc_agent.cli --scenario uc1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .agent import run
from .config import ROOT

SCENARIOS = ROOT / "scenarios" / "scenarios.yaml"


def load_scenario(name: str) -> dict:
    data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    if name not in data:
        raise SystemExit(f"Scénario inconnu : {name}. Disponibles : {', '.join(data)}")
    return data[name]


def main() -> None:
    parser = argparse.ArgumentParser(description="Interroger GRC-Agent")
    parser.add_argument("question", nargs="?", help="question en langage naturel")
    parser.add_argument("--user", default="u.dupont", help="identifiant utilisateur (table users)")
    parser.add_argument("--scenario", help="scénario prédéfini de scenarios/scenarios.yaml")
    parser.add_argument("--json", action="store_true", help="affiche la trace complète en JSON")
    args = parser.parse_args()

    if args.scenario:
        sc = load_scenario(args.scenario)
        question, user = sc["question"], sc.get("user", args.user)
    elif args.question:
        question, user = args.question, args.user
    else:
        parser.error("indiquer une question ou --scenario")

    result = run(question, user_id=user, scenario=args.scenario)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("\n=== Appels d'outils ===")
    for c in result["appels_outils"]:
        flag = "  <-- ÉCRITURE" if c["niveau_cible"] in ("N2", "N3") else ""
        print(f"- [{c['niveau_cible']}] {c['outil']}({json.dumps(c['arguments'], ensure_ascii=False)}){flag}")
    print("\n=== Réponse ===")
    print(result["reponse"])
    print(f"\n({result['duree_s']} s, {len(result['ecritures'])} écriture(s), trace : {result['trace']})")


if __name__ == "__main__":
    main()
