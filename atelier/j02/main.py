from outils import risques_hors_appetit, exporter_json, compter_par_famille 
try:
    hors = risques_hors_appetit()
    
except FileNotFoundError as erreur:
    print("Fichier introuvable :", erreur.filename)
except ValueError as erreur:
    print("Donnée invalide :", erreur)
else:
    print(len(hors), "risques hors appétit")
    chemin = exporter_json(hors, "hors_appetit.json")
    print("Exporté :", chemin)

familles = compter_par_famille(hors)
print(familles)


