"""Tests de bout en bout de l'agent J3, avec un LLM simulé (pas besoin d'Ollama).

Le modèle simulé rejoue une suite d'appels d'outils : on vérifie que le graphe
LangGraph exécute bien les outils sur la vraie base PostgreSQL, que la trace est
écrite, et que la version de référence est bien SANS protection (faille M1).
"""
import os

import pytest

pytest.importorskip("langchain")
psycopg = pytest.importorskip("psycopg")

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from grc_agent import agent as agent_mod  # noqa: E402
from grc_agent import db  # noqa: E402
from grc_agent import tools  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL")


class ScriptedModel(BaseChatModel):
    """Renvoie à chaque appel le message suivant d'un script prédéfini."""

    script: list

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self.script.pop(0)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def call(name, args, i):
    return AIMessage(content="", tool_calls=[{"id": f"call_{i}", "name": name, "args": args}])


class FakeCollection:
    META = {"title": "DORA", "source_id": "REG-DORA", "article": "Art. 30", "norm_level": 1, "position": 0}

    def query(self, query_texts, n_results, where=None):
        return {"documents": [["Article 30 — Dispositions contractuelles clés …"]], "metadatas": [[self.META]]}

    def get(self, where=None, include=None):
        return {"documents": ["Article 30 — Dispositions contractuelles clés …"], "metadatas": [self.META]}


@pytest.fixture
def base():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL non défini")
    try:
        psycopg.connect(DATABASE_URL, connect_timeout=3).close()
    except psycopg.OperationalError:
        pytest.skip("base PostgreSQL injoignable (lancer `make up`)")
    db.configure(DATABASE_URL)
    yield
    # Remet la base dans son état initial
    db.execute("DELETE FROM risks WHERE id > 'R-030'")
    db.execute("DELETE FROM obligations WHERE id > 'O-025'")
    db.execute("UPDATE incidents SET status = 'ouvert' WHERE id = 'I-010'")


@pytest.fixture
def traces(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_mod, "TRACES_DIR", tmp_path)
    monkeypatch.setattr(agent_mod, "ROOT", tmp_path.parent)
    return tmp_path


def test_uc1_ajoute_un_risque_et_le_relie(base, traces):
    script = [
        call("lister_risques", {"processus": "Entrée en relation"}, 1),
        call("ajouter_risque", {
            "titre": "Contournement de la vérification d'identité en ligne",
            "description": "Selfie ou pièce falsifiée acceptés par le prestataire de vérification.",
            "categorie": "OP-FE", "processus": "Ouverture de compte en ligne", "unite": "RET",
            "vraisemblance_brute": 4, "impact_brut": 4,
            "vraisemblance_residuelle": 2, "impact_residuel": 3}, 2),
        call("lier_risque_controle", {"risk_id": "R-031", "control_id": "C-028"}, 3),
        AIMessage(content="J'ai ajouté le risque R-031 et l'ai relié au contrôle C-028."),
    ]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    result = agent_mod.run("Analyse le processus d'ouverture de compte en ligne.", "u.dupont",
                           agent=agent, scenario="test-uc1")

    assert [c["outil"] for c in result["appels_outils"]] == ["lister_risques", "ajouter_risque", "lier_risque_controle"]
    assert len(result["ecritures"]) == 2
    assert "R-015" in result["appels_outils"][0]["resultat"]          # risque existant retrouvé
    row = db.fetch_all("SELECT residual_score FROM risks WHERE id = 'R-031'")
    assert row == [{"residual_score": 6}]
    assert db.fetch_all("SELECT 1 FROM risk_controls WHERE risk_id = 'R-031' AND control_id = 'C-028'")
    assert list(traces.glob("*.jsonl"))
    assert result["actions_non_executees"] == []   # « ajouté » et « relié » sont prouvés par la trace


def test_uc2_cite_dora_et_ajoute_une_obligation(base, traces):
    script = [
        call("rechercher_textes", {"question": "DORA article 30 dispositions contractuelles"}, 1),
        call("lister_obligations", {"reglementation": "REG-DORA"}, 2),
        call("ajouter_obligation", {"reglementation": "REG-DORA", "article": "Art. 30, par. 3",
                                    "resume": "Clauses supplémentaires pour les fonctions critiques ou importantes.",
                                    "unite": "CMP"}, 3),
        call("lier_obligation_controle", {"obligation_id": "O-026", "control_id": "C-014"}, 4),
        AIMessage(content="Obligation O-026 ajoutée (DORA, art. 30, par. 3) et reliée à C-014."),
    ]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    result = agent_mod.run("Cartographie DORA article 30.", "u.weber", agent=agent)

    assert "Art. 30" in result["appels_outils"][0]["resultat"]
    assert db.fetch_all("SELECT article FROM obligations WHERE id = 'O-026'") == [{"article": "Art. 30, par. 3"}]


def test_reference_sans_protection_autorise_une_action_n3(base, traces):
    """Faille ATTENDUE en J3 (menace M1) : un utilisateur métier fait clôturer un incident
    par l'agent. Ce test devra être inversé quand la couche d'autorité sera en place (S2)."""
    script = [call("cloturer_incident", {"incident_id": "I-010"}, 1), AIMessage(content="Incident clos.")]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    result = agent_mod.run("Clôture l'incident I-010.", "u.muller", agent=agent)

    assert result["ecritures"][0]["niveau_cible"] == "N3"
    assert db.fetch_all("SELECT status FROM incidents WHERE id = 'I-010'") == [{"status": "clos"}]


def test_progression_affichee_a_chaque_etape(base, traces):
    script = [call("risques_hors_appetit", {}, 1), AIMessage(content="6 risques hors appétit.")]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    events = []
    agent_mod.run("Risques hors appétit ?", "u.dupont", agent=agent, on_event=lambda k, d: events.append((k, d)))

    assert [k for k, _ in events] == ["debut", "appel", "resultat", "reponse"]
    assert events[1][1]["outil"] == "risques_hors_appetit" and events[1][1]["niveau"] == "N0"


def test_alerte_si_le_modele_simule_les_appels(base, traces):
    """Comportement observé avec mistral:7b en J3 : appels écrits en JSON dans le texte,
    résultats inventés, aucun outil exécuté. L'agent doit le signaler."""
    texte = ('[{"name":"rechercher_textes","arguments":{"question":"DORA art. 30"}}]\n'
             "L'article 30 impose…\n"
             '[{"name":"obligations_sans_controle_efficace","arguments":{}}]\nIl n\'y a pas d\'écarts.')
    agent = agent_mod.build_agent(model=ScriptedModel(script=[AIMessage(content=texte)]), collection=FakeCollection())
    result = agent_mod.run("Cartographie DORA article 30.", "u.weber", agent=agent)

    assert result["appels_outils"] == []
    assert result["appels_simules"] == ["rechercher_textes", "obligations_sans_controle_efficace"]


def test_pas_d_alerte_quand_les_outils_sont_vraiment_appeles(base, traces):
    script = [call("risques_hors_appetit", {}, 1), AIMessage(content="6 risques hors appétit.")]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    assert agent_mod.run("Risques hors appétit ?", "u.dupont", agent=agent)["appels_simules"] == []


def test_relance_quand_le_modele_annonce_un_outil_sans_l_appeler(base, traces):
    """Comportement observé avec qwen2.5:7b : « Je vais utiliser la fonction lister_obligations… » puis arrêt."""
    script = [
        AIMessage(content="Ensuite, je vais utiliser la fonction `lister_obligations` pour vérifier le référentiel."),
        call("lister_obligations", {"reglementation": "REG-DORA"}, 1),
        AIMessage(content="Le référentiel contient les obligations DORA suivantes : …"),
    ]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    events = []
    result = agent_mod.run("Cartographie DORA article 30.", "u.weber", agent=agent,
                           on_event=lambda k, d: events.append(k))

    assert result["relances"] == 1 and "relance" in events
    assert [c["outil"] for c in result["appels_outils"]] == ["lister_obligations"]
    assert result["reponse"].startswith("Le référentiel")


def test_alerte_si_la_reponse_affirme_des_actions_non_executees(base, traces):
    """Comportement observé avec qwen2.5:7b (UC2) : actions racontées, 0 écriture."""
    script = [
        call("lister_obligations", {"reglementation": "REG-DORA"}, 1),
        AIMessage(content="Obligation O-013 ajoutée et reliée à C-014. L'efficacité de C-009 a été mise à jour. "
                          "L'incident I-001 est maintenant clôturé."),
    ]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    result = agent_mod.run("Cartographie DORA article 30.", "u.weber", agent=agent)

    assert result["ecritures"] == []
    assert result["actions_non_executees"] == ["ajout", "liaison", "modification", "clôture"]


def test_pas_d_alerte_pour_une_intention_future(base, traces):
    script = [AIMessage(content="Je vais ajouter les obligations manquantes puis les relier aux contrôles.")]
    agent = agent_mod.build_agent(model=ScriptedModel(script=script), collection=FakeCollection())
    assert agent_mod.run("Cartographie DORA.", "u.weber", agent=agent)["actions_non_executees"] == []


def test_lister_obligations_filtre_par_article_et_donne_l_efficacite(base):
    """UC2 avec qwen2.5:7b : sans filtre ni efficacité, le modèle a inventé 10 obligations
    « couvertes efficacement » ; le référentiel n'en contient qu'une (O-015, C-014 partiel)."""
    from grc_agent import tools

    rows = tools.lister_obligations.invoke({"reglementation": "REG-DORA", "article": "30"})
    assert [r["id"] for r in rows] == ["O-015"]
    assert rows[0]["controles"] == "C-014 (partiel)"
    assert tools.lister_obligations.invoke({"reglementation": "REG-DORA", "article": "3"})[0].get("resultat")
    sans = [r for r in tools.lister_obligations.invoke({"reglementation": "REG-DORA"}) if r["id"] == "O-010"]
    assert sans[0]["controles"] == "aucun contrôle"


def test_texte_des_blocs_gemini():
    """Gemini 3 renvoie une liste de blocs (texte + signature de réflexion) : on ne garde que le texte."""
    contenu = [{"type": "text", "text": "Bonjour"}, {"type": "text", "text": " !", "extras": {"signature": "abc"}}]
    assert agent_mod.message_text(contenu) == "Bonjour !"
    assert agent_mod.message_text("réponse simple") == "réponse simple"


def test_outil_annonce_dans_des_blocs():
    msg = AIMessage(content=[{"type": "text", "text": "Je vais utiliser lister_obligations."}])
    assert agent_mod.announced_tool(msg) == "lister_obligations"


def test_ajouts_paralleles_sans_collision_d_identifiant(base):
    """Gemini appelle plusieurs outils en parallèle : deux ajouts simultanés ne doivent pas
    calculer le même identifiant (UniqueViolation sur obligations_pkey, observé le 31 octobre)."""
    from concurrent.futures import ThreadPoolExecutor

    args = {"reglementation": "REG-DORA", "article": "Art. 28", "resume": "test d'ajout parallèle", "unite": "CMP"}
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: tools.ajouter_obligation.invoke(args)["id"], range(4)))
    assert len(set(ids)) == 4


def test_une_erreur_pendant_le_passage_est_tracee(base, traces):
    """Un passage interrompu par une erreur doit quand même laisser une trace (traçabilité, M8)."""

    class AgentEnPanne:
        def stream(self, *args, **kwargs):
            raise RuntimeError("panne simulée")

    result = agent_mod.run("Question de test", agent=AgentEnPanne(), scenario="test")
    assert "panne simulée" in result["erreur"]
    lignes = list(traces.glob("*.jsonl"))[0].read_text(encoding="utf-8").splitlines()
    assert "panne simulée" in lignes[-1]
