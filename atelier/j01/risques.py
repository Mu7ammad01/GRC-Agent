import csv
import json

appetit = {}
with open ("j01/risk_appetite.csv" , encoding="utf-8") as f : 
    for ligne in csv.DictReader(f) :
        appetit[ligne["family"]] = int(ligne["max_residual_score"])
# print(appetit)
categories = {}
with open("j01/risk_categories.csv" , encoding="utf-8") as f:
    for ligne in csv.DictReader(f) :
        categories[ligne["id"]] = ligne["family"]
# print(categories)
def risques_hors_appetit():
    resultat = []
    with open("j01/risks.csv" , encoding="utf-8") as f:
        lecteur = csv.DictReader(f)
        for risque in lecteur : 
            famille = categories[risque["category_id"]]
            seuil = appetit[famille]
            score = int(risque["residual_likelihood"]) * int(risque["residual_impact"])
            if score > seuil :
                resultat.append({"id" : risque["id"], "titre": risque["title"], "famille": famille, "score": score, "seuil": seuil})
    return resultat
hors = risques_hors_appetit()
print(len(hors), "risques hors appétit")
for r in hors:
    print(r)

with open("j01/hors_appetit.json", "w", encoding="utf-8") as f : 
    json.dump(hors, f, ensure_ascii=False, indent=2)
print("Export terminé : j01/hors_appetit.json")  


