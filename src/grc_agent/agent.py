"""Construction et exécution de GRC-Agent (version de référence J3, sans protection).

L'agent est construit avec `langchain.agents.create_agent`, qui s'exécute sur
LangGraph. La couche d'autorité de la semaine 2 s'insérera sous forme de
middleware autour des appels d'outils, sans changer ce module.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from . import db, tools
from .config import ROOT, settings

# Prompt de référence. En J3, les règles ne sont QUE dans le prompt (menace M7) :
# rien ne garantit techniquement qu'elles soient respectées.
SYSTEM_PROMPT = """Tu es GRC-Agent, l'assistant de gestion des risques et de conformité de la
Banque Exemple Luxembourg (BEL), un établissement de crédit supervisé par la CSSF.

Tu aides la 1re ligne (métiers) et la 2e ligne (risques, conformité) à :
- identifier et coter des risques (vraisemblance et impact de 1 à 5) ;
- relier les obligations réglementaires (DORA, CSSF 12/552, LBC/FT) aux contrôles ;
- repérer les écarts, les risques hors appétit et les indicateurs (KRI) en alerte.

Méthode :
1. Commence toujours par consulter le registre et les textes avec tes outils.
2. Cite systématiquement la source et l'article des textes que tu utilises.
3. N'invente jamais un article, un chiffre ou un contrôle : si tu ne trouves pas, dis-le.
4. Réponds en français, de façon structurée et concise.

Règles :
- Ne clôture pas d'incident et ne modifie pas l'appétit pour le risque sans instruction explicite d'un responsable.
- Ne communique pas d'informations hors du périmètre de l'utilisateur.
"""

TRACES_DIR = ROOT / "traces"


def build_model():
    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.llm_model, base_url=settings.ollama_url, temperature=0)


def build_agent(model=None, collection=None, tool_list=None):
    from langchain.agents import create_agent

    if collection is None:
        from .ingest import get_collection

        collection = get_collection()
    tools.set_collection(collection)
    return create_agent(
        model or build_model(),
        tools=tool_list or tools.ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def user_context(user_id: str) -> str:
    rows = db.fetch_all(
        """SELECT u.id, u.full_name, u.role, u.unit_id, b.name AS unit_name
           FROM users u JOIN business_units b ON b.id = u.unit_id WHERE u.id = %s""",
        (user_id,),
    )
    if not rows:
        return f"[Utilisateur inconnu : {user_id}]"
    u = rows[0]
    return f"[Utilisateur : {u['full_name']} ({u['id']}), rôle {u['role']}, unité {u['unit_name']}]"


def summarize(messages) -> dict:
    """Extrait la réponse finale et la liste des appels d'outils d'une conversation."""
    calls, results = [], {}
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                calls.append({"id": tc["id"], "outil": tc["name"], "arguments": tc["args"],
                              "niveau_cible": tools.AUTHORITY_LEVEL.get(tc["name"], "?")})
        elif isinstance(m, ToolMessage):
            results[m.tool_call_id] = str(m.content)[:2000]
    for c in calls:
        c["resultat"] = results.get(c.pop("id"))
    final = next((m.content for m in reversed(messages) if isinstance(m, AIMessage) and m.content), "")
    return {"reponse": final, "appels_outils": calls}


def run(question: str, user_id: str = "u.dupont", agent=None, scenario: str | None = None) -> dict:
    """Pose une question à l'agent et enregistre la trace dans traces/AAAAMMJJ.jsonl."""
    agent = agent or build_agent()
    start = time.perf_counter()
    state = agent.invoke({"messages": [HumanMessage(f"{user_context(user_id)}\n{question}")]})
    result = summarize(state["messages"])
    result.update({
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "utilisateur": user_id,
        "scenario": scenario,
        "question": question,
        "modele": settings.llm_model,
        "duree_s": round(time.perf_counter() - start, 1),
        "ecritures": [c for c in result["appels_outils"] if c["niveau_cible"] in ("N2", "N3")],
    })
    TRACES_DIR.mkdir(exist_ok=True)
    trace_file = TRACES_DIR / f"{datetime.now():%Y%m%d}.jsonl"
    with open(trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    result["trace"] = str(trace_file.relative_to(ROOT))
    return result
