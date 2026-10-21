import json
import csv
from pathlib import Path
DOSSIER = Path(__file__).parent

def charger_appetit():
    """renvoie le seuil d'appétit de chaque famille, ex. {"tic": 9}. """
    appetit = {}
    with open(DOSSIER / "risk_appetite.csv", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            appetit[ligne["family"]] = int(ligne["max_residual_score"])
    return appetit

def charger_categories():
    """Renvoie la famille de chaque catégorie, ex. {"TIC-CYB": "tic"}."""    
    categories = {}
    with open(DOSSIER / "risk_categories.csv", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            categories[ligne["id"]] = ligne["family"]
    return categories

def note_valide(texte, colonne, id_risque):
    """Convertit une note en entier et vérifie qu'elle est entre 1 et 5."""
    note = int(texte)
    if not 1<= note <=5 :
        raise ValueError(f"{id_risque} : {colonne} = {note}, attendu entre 1 et 5") 
    return note

def risques_hors_appetit():
    from outils import charger_appetit
    from outils import charger_categories
    appetit = charger_appetit()
    categories = charger_categories()
  
    resultat = []
    with open(DOSSIER / "risks.csv" , encoding="utf-8") as f:
        lecteur = csv.DictReader(f)
        for risque in lecteur : 
            famille = categories[risque["category_id"]]
            seuil = appetit[famille]
            # score = int(risque["residual_likelihood"]) * int(risque["residual_impact"])
            vraisemblance = note_valide(risque["residual_likelihood"], "residual_likelihood", risque["id"])
            impact = note_valide(risque["residual_impact"],"residual_impact", risque["id"] )
            score = vraisemblance * impact

            if score > seuil :
                resultat.append({"id" : risque["id"], "titre": risque["title"], "famille": famille, "score": score, "seuil": seuil})
    return resultat

def exporter_json(donnees, nom_fichier):
    """Écrit des données en JSON à côté du module et renvoie le chemin du fichier."""
    chemin = DOSSIER / nom_fichier
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    return chemin

hors=risques_hors_appetit()
def compter_par_famille(risques):
    """Renvoie le nombre de risques par famille, ex. {"tic": 3}."""
    compte = {}
    for r in risques:
       compte[r["famille"]] = compte.get(r["famille"], 0) + 1
    return compte
