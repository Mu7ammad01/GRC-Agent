"""Interface web locale de GRC-Agent (intranet).

Sert une page de chat qui interroge l'agent et affiche, à côté de la réponse,
la « gouvernance » de l'échange : outils appelés (N0/N2/N3) et journal d'audit
(actions autorisées ou refusées). Lancement :

    PYTHONPATH=src uvicorn web.app:app --reload
"""
import os
from pathlib import Path

# Charger .env : le code lit os.getenv et uvicorn ne charge pas .env tout seul.
RACINE = Path(__file__).resolve().parents[1]
_env = RACINE / ".env"
if _env.exists():
    for ligne in _env.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, val = ligne.split("=", 1)
            os.environ.setdefault(cle.strip(), val.strip())

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from grc_agent import agent as agent_mod, db  # noqa: E402

FOURNISSEUR = "google_genai"
MODELE = os.getenv("LLM_MODEL_WEB", "gemini-3.8-flash")

app = FastAPI(title="GRC-Agent · interface web")
_AGENT = None

# Démo publique : borne le nombre de requêtes/heure pour limiter les coûts Vertex.
import time as _temps  # noqa: E402
_HITS: list[float] = []
_LIMITE_HEURE = int(os.getenv("DEMO_LIMITE_HEURE", "80"))


def _quota_ok() -> bool:
    maintenant = _temps.time()
    _HITS[:] = [t for t in _HITS if maintenant - t < 3600]
    if len(_HITS) >= _LIMITE_HEURE:
        return False
    _HITS.append(maintenant)
    return True


def _agent():
    """Construit l'agent une seule fois (collection RAG + modèle), puis le réutilise."""
    global _AGENT
    if _AGENT is None:
        _AGENT = agent_mod.build_agent(model=agent_mod.build_model(FOURNISSEUR, MODELE))
    return _AGENT


def _audit_max():
    return db.fetch_all("SELECT COALESCE(MAX(id), 0) AS m FROM audit_log")[0]["m"]


class Question(BaseModel):
    question: str
    utilisateur: str = "u.dupont"


@app.get("/", response_class=HTMLResponse)
def accueil():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@app.get("/utilisateurs")
def utilisateurs():
    """Liste des utilisateurs pour le sélecteur de rôle."""
    return db.fetch_all("SELECT id, full_name, role FROM users ORDER BY role, id")


@app.get("/sante")
def sante():
    return {"statut": "ok", "modele": MODELE}


@app.post("/ask")
def ask(q: Question):
    """Pose la question à l'agent et renvoie la réponse + la gouvernance de l'échange."""
    if not _quota_ok():
        return {"reponse": "Démonstration en pause (limite horaire atteinte pour maîtriser les coûts). "
                           "Réessayez dans un moment, ou lancez le projet en local depuis le dépôt GitHub.",
                "outils": [], "audit": [], "ecritures": 0, "duree_s": 0, "erreur": None}
    avant = _audit_max()
    res = agent_mod.run(q.question, user_id=q.utilisateur, agent=_agent(),
                        provider=FOURNISSEUR, model_name=MODELE)
    audit = db.fetch_all(
        "SELECT actor, event, authority_level, decision FROM audit_log WHERE id > %s ORDER BY id",
        (avant,),
    )
    return {
        "reponse": res["reponse"],
        "outils": [{"outil": c["outil"], "niveau": c["niveau_cible"]} for c in res["appels_outils"]],
        "audit": audit,
        "ecritures": len(res["ecritures"]),
        "duree_s": res["duree_s"],
        "erreur": res.get("erreur"),
    }
