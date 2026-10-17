seuil=9
print(seuil)
famille= "tic"
print(f"Le seuil de la famille {famille} est {seuil}")
appetit = {"operationnel": 12, "tic": 9, "conformite": 6}
print(appetit["tic"])
for famille, seuil_max in appetit.items():
    if seuil_max < 10:
        print(f"{famille} : tolérance faible ({seuil_max})")

def score(vraisemblance, impact):
     return(vraisemblance*impact)
print(score(2,5))
print(score(2,5) > appetit["tic"])