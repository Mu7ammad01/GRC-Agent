import csv

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
with open("j01/risks.csv" , encoding="utf-8") as f:
    lecteur = csv.DictReader(f)
    for risque in lecteur : 
        famille = categories[risque["category_id"]]
        seuil = appetit[famille]
        score = int(risque["residual_likelihood"]) * int(risque["residual_impact"])
        if score > seuil :
            print(risque["id"], famille, score, ">", seuil)
            
