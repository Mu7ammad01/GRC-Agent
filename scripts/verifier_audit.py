"""Vérifie l'intégrité du journal d'audit (chaînage par empreinte)."""
import hashlib
import json

from grc_agent import db


def corps(l, prev):
    return json.dumps({"acteur": l["actor"], "evenement": l["event"], "niveau": l["authority_level"],
                       "decision": l["decision"], "payload": l["payload"], "prev_hash": prev},
                      sort_keys=True, ensure_ascii=False)


def main():
    lignes = db.fetch_all("SELECT * FROM audit_log ORDER BY id")
    prev = None
    for l in lignes:
        attendu = hashlib.sha256(corps(l, prev).encode("utf-8")).hexdigest()
        etat = "OK" if attendu == l["hash"] and l["prev_hash"] == prev else "ROMPU"
        print(f"{l['id']:>3} {l['event']:<30} {l['decision']:<10} {etat}")
        if etat == "ROMPU":
            print("  -> chaine rompue a cette ligne")
            return
        prev = l["hash"]
    print(f"\n{len(lignes)} ligne(s), chaine integre.")


if __name__ == "__main__":
    main()