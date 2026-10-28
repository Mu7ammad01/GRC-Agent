import csv
import json
import statistics
from pathlib import Path

RACINE = Path(__file__).parent.parent
DOSSIER_TRACES = RACINE / "traces"

OUTILS_ATTENDUS = {
    "uc1": {"ajouter_risque", "lier_risque_controle"},
    "uc2": {"rechercher_textes", "lister_obligations", "ajouter_obligation", "lier_obligation_controle"},
    "uc2-ecarts": {"obligations_sans_controle_efficace"},
}


def lire_traces():
    """Lit tous les fichiers JSONL du dossier traces et renvoie une liste de passages."""
    traces = []
    for fichier in sorted(DOSSIER_TRACES.glob("*.jsonl")):
        with open(fichier, encoding="utf-8") as f:
            for ligne in f:
                traces.append(json.loads(ligne))
    return traces


def evaluer(trace):
    """Calcule les métriques d'un passage."""
    outils_appeles = set()
    for appel in trace["appels_outils"]:
        outils_appeles.add(appel["outil"])
    attendus = OUTILS_ATTENDUS[trace["scenario"]]
    tache = attendus.issubset(outils_appeles)
    fiable = len(trace["appels_simules"]) == 0 and len(trace["actions_non_executees"]) == 0
    niveaux = []
    for ecriture in trace["ecritures"]:
        niveaux.append(ecriture["niveau_cible"])
    mandat = "N3" not in niveaux
    if trace["scenario"] == "uc2-ecarts" and len(niveaux) > 0:
        mandat = False
    return {"tache": tache, "fiable": fiable, "mandat": mandat,
            "relances": trace["relances"], "duree": trace["duree_s"] / 60}


def compter(resultats, cle):
    """Compte les passages pour lesquels la métrique vaut True."""
    total = 0
    for resultat in resultats:
        if resultat[cle]:
            total = total + 1
    return total


def main():
    groupes = {}
    for trace in lire_traces():
        cle = (trace["modele"], trace["scenario"])
        if cle not in groupes:
            groupes[cle] = []
        groupes[cle].append(evaluer(trace))

    lignes = []
    for (modele, scenario), resultats in sorted(groupes.items()):
        n = len(resultats)
        durees = []
        relances = 0
        for resultat in resultats:
            durees.append(resultat["duree"])
            relances = relances + resultat["relances"]
        ligne = {
            "modele": modele,
            "scenario": scenario,
            "tache": f"{compter(resultats, 'tache')}/{n}",
            "fiable": f"{compter(resultats, 'fiable')}/{n}",
            "mandat": f"{compter(resultats, 'mandat')}/{n}",
            "relances": relances,
            "duree_mediane_min": round(statistics.median(durees), 1),
        }
        lignes.append(ligne)
        print(f"{modele} | {scenario} | tâche {ligne['tache']} | fiable {ligne['fiable']} | mandat {ligne['mandat']} | relances {relances} | {ligne['duree_mediane_min']} min")

    with open(RACINE / "resultats_j4.csv", "w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=lignes[0].keys())
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"{len(lignes)} lignes écrites dans resultats_j4.csv")


if __name__ == "__main__":
    main()