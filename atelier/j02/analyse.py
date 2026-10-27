from pathlib import Path
import pandas as pd

DOSSIER = Path(__file__).parent
risques = pd.read_csv(DOSSIER / "risks.csv")

""" print(risques.shape)
print(risques.head)
print(risques.dtypes)
"""

# " Etape 2"

risques["score_inherent"] = risques["inherent_likelihood"]*risques["inherent_impact"]
risques["score_residuel"] = risques["residual_likelihood"]*risques["residual_impact"]
print(risques[["id", "score_inherent", "score_residuel"]].head())


"Etape 3"

categories = pd.read_csv(DOSSIER / "risk_categories.csv")
appetit = pd.read_csv(DOSSIER / "risk_appetite.csv")
complet = risques.merge(categories[["id", "family"]], left_on="category_id", right_on="id", suffixes=("", "_cat"))
complet = complet.merge(appetit[["family", "max_residual_score"]], on="family")

hors = complet[complet["score_residuel"] > complet["max_residual_score"]]
print(hors[["id", "family", "score_residuel", "max_residual_score"]])