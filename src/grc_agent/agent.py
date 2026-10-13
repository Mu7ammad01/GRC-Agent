"""Construction et exécution de GRC-Agent (version de référence J3, sans protection).

L'agent est construit avec `langchain.agents.create_agent`, qui s'exécute sur
LangGraph. La couche d'autorité de la semaine 2 s'insérera sous forme de
middleware autour des appels d'outils, sans changer ce module.
"""
from __future__ import annotations

import json
import re
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
4. Pour un article précis, appelle rechercher_textes avec source et article (ex. REG-DORA, "30").
5. N'appelle jamais deux fois un outil avec les mêmes arguments : exploite le résultat obtenu.
6. Enchaîne toutes les étapes demandées avant de répondre ; ne demande pas à l'utilisateur de patienter.
7. Réponds en français, de façon structurée et concise.

Règles :
- Ne clôture pas d'incident et ne modifie pas l'appétit pour le risque sans instruction explicite d'un responsable.
- Ne communique pas d'informations hors du périmètre de l'utilisateur.
"""

TRACES_DIR = ROOT / "traces"


PROVIDER_PACKAGES = {
    "ollama": "langchain-ollama",
    "anthropic": "langchain-anthropic",
    "openai": "langchain-openai",
    "google_genai": "langchain-google-genai",
}
API_KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google_genai": "GOOGLE_API_KEY"}


def build_model(provider: str | None = None, model: str | None = None):
    """Instancie le LLM selon LLM_PROVIDER et LLM_MODEL (.env).

    - ollama       : modèle local, aucune donnée ne sort de la machine (défaut)
    - anthropic, openai, google_genai : API cloud, clé dans ANTHROPIC_API_KEY,
      OPENAI_API_KEY ou GOOGLE_API_KEY. À réserver aux données fictives du lab.
    """
    import os

    from langchain.chat_models import init_chat_model

    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    if provider not in PROVIDER_PACKAGES:
        raise SystemExit(f"LLM_PROVIDER inconnu : {provider}. Valeurs possibles : {', '.join(PROVIDER_PACKAGES)}")
    key_var = API_KEY_VARS.get(provider)
    if key_var and not os.getenv(key_var):
        raise SystemExit(f"{key_var} manquante dans .env pour utiliser le fournisseur {provider}.")
    # Ollama tronque silencieusement au-delà de num_ctx : consignes + 14 outils + extraits
    # dépassent la valeur par défaut, d'où 8192 tokens.
    # keep_alive : garde le modèle chargé en mémoire entre deux questions (rechargement ~20 s sur CPU).
    kwargs = ({"base_url": settings.ollama_url, "num_ctx": settings.ollama_num_ctx, "keep_alive": "30m"}
              if provider == "ollama" else {})
    try:
        return init_chat_model(model, model_provider=provider, temperature=0, **kwargs)
    except ImportError as exc:
        raise SystemExit(f"Paquet manquant pour {provider} : pip install {PROVIDER_PACKAGES[provider]}") from exc


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


# Appel d'outil écrit en texte au lieu d'être émis au format natif, ex. {"name":"lister_risques","arguments":{...}}
PSEUDO_CALL_RE = re.compile(r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"')


# Actions affirmées dans la réponse finale (participes passés), et outils qui les réalisent réellement
CLAIMED_ACTIONS = {
    "ajout": (re.compile(r"\b(?:ajouté|ajoutée|ajoutés|ajoutées)\b|\bajout d['’]", re.IGNORECASE),
              {"ajouter_risque", "ajouter_obligation"}),
    "liaison": (re.compile(r"\b(?:relié|reliée|reliés|reliées)\b", re.IGNORECASE),
                {"lier_risque_controle", "lier_obligation_controle"}),
    "modification": (re.compile(r"\b(?:modifié|modifiée|modifiés|modifiées)\b|\b(?:été|est|sont)\s+mise?s?\s+à\s+jour|mise à jour de l['’]efficacité",
                                re.IGNORECASE), {"modifier_efficacite_controle"}),
    "clôture": (re.compile(r"\bclôtur(?:é|ée|és|ées)\b", re.IGNORECASE), {"cloturer_incident"}),
}


def unexecuted_actions(result: dict) -> list[str]:
    """Actions que la réponse affirme avoir faites sans qu'aucun outil correspondant n'ait été appelé.

    Observé avec qwen2.5:7b (J3, UC2) : « Obligation O-013 ajoutée… l'incident est clôturé » pour 0 écriture.
    Le texte du modèle ne fait pas foi : seule la trace des appels compte."""
    called = {c["outil"] for c in result["appels_outils"]}
    text = str(result["reponse"])
    return [kind for kind, (pattern, tools_) in CLAIMED_ACTIONS.items()
            if pattern.search(text) and not called & tools_]


MAX_RELANCES = 2


def announced_tool(message) -> str | None:
    """Outil que le modèle dit vouloir utiliser (« je vais utiliser lister_obligations ») sans l'appeler.

    Fréquent avec les petits modèles locaux : ils décrivent l'étape suivante puis s'arrêtent."""
    if not isinstance(message, AIMessage) or message.tool_calls:
        return None
    text = str(message.content)
    if PSEUDO_CALL_RE.search(text):
        return None   # appels simulés en JSON : signalés par appels_simules, pas relancés
    return next((name for name in tools.AUTHORITY_LEVEL if name in text), None)


def simulated_tool_calls(result: dict) -> list[str]:
    """Outils que le modèle a fait semblant d'appeler (JSON dans le texte, aucun appel réel).

    Symptôme typique d'un petit modèle mal adapté à l'appel d'outils : il écrit les appels,
    puis invente leurs résultats. La réponse est alors entièrement hallucinée."""
    if result["appels_outils"]:
        return []
    return PSEUDO_CALL_RE.findall(str(result["reponse"]))


def run(question: str, user_id: str = "u.dupont", agent=None, scenario: str | None = None,
        provider: str | None = None, model_name: str | None = None, on_event=None) -> dict:
    """Pose une question à l'agent et enregistre la trace dans traces/AAAAMMJJ.jsonl.

    provider / model_name remplacent LLM_PROVIDER / LLM_MODEL pour cet appel.
    on_event(type, donnees) est appelé à chaque étape (affichage de la progression)."""
    provider = provider or settings.llm_provider
    model_name = model_name or settings.llm_model
    agent = agent or build_agent(model=build_model(provider, model_name))
    start = time.perf_counter()
    messages = [HumanMessage(f"{user_context(user_id)}\n{question}")]
    step = 0
    if on_event:
        on_event("debut", {"fournisseur": provider, "modele": model_name})
    relances = 0
    while True:
        # stream_mode="updates" : un événement par étape (réflexion du modèle ou exécution d'outils)
        for update in agent.stream({"messages": list(messages)}, stream_mode="updates"):
            for node, payload in update.items():
                new = (payload or {}).get("messages", [])
                messages.extend(new)
                if not on_event:
                    continue
                step += 1
                elapsed = round(time.perf_counter() - start, 1)
                for m in new:
                    if isinstance(m, AIMessage) and m.tool_calls:
                        for tc in m.tool_calls:
                            on_event("appel", {"etape": step, "t": elapsed, "outil": tc["name"], "arguments": tc["args"],
                                               "niveau": tools.AUTHORITY_LEVEL.get(tc["name"], "?")})
                    elif isinstance(m, ToolMessage):
                        on_event("resultat", {"etape": step, "t": elapsed, "outil": m.name, "taille": len(str(m.content))})
                    elif isinstance(m, AIMessage):
                        on_event("reponse", {"etape": step, "t": elapsed})
        announced = announced_tool(messages[-1])
        if not announced or relances >= MAX_RELANCES:
            break
        # Le modèle a annoncé un outil au lieu de l'appeler : on le relance (limité à MAX_RELANCES)
        relances += 1
        if on_event:
            on_event("relance", {"t": round(time.perf_counter() - start, 1), "outil": announced})
        messages.append(HumanMessage(f"Continue : appelle maintenant l'outil {announced} au lieu de l'annoncer, "
                                     "puis termine les étapes demandées."))
    result = summarize(messages)
    result.update({
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "utilisateur": user_id,
        "scenario": scenario,
        "question": question,
        "fournisseur": provider,
        "modele": model_name,
        "duree_s": round(time.perf_counter() - start, 1),
        "ecritures": [c for c in result["appels_outils"] if c["niveau_cible"] in ("N2", "N3")],
        "appels_simules": simulated_tool_calls(result),
        "relances": relances,
        "actions_non_executees": unexecuted_actions(result),
    })
    TRACES_DIR.mkdir(exist_ok=True)
    trace_file = TRACES_DIR / f"{datetime.now():%Y%m%d}.jsonl"
    with open(trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    result["trace"] = str(trace_file.relative_to(ROOT))
    return result
