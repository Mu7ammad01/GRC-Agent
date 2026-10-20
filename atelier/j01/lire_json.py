import json

with open("j01/hors_appetit.json", "r", encoding="utf-8") as f :
    risques = json.load(f)
print(len(risques), "risques relus")
ecarts=[]
for r in risques:
    e.append(r["score"] - r["seuil"])

print(max(e))
ecart_max= max(e)
for r in risques:
    if r["score"] - r["seuil"] == E:
        print(r["id"], r["titre"], ", L'écart entre score et seuil est :", E)
