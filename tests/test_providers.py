"""Choix du fournisseur de LLM (sans appel réseau : on instancie seulement les clients)."""
import pytest

pytest.importorskip("langchain")

from grc_agent.agent import build_model  # noqa: E402


def test_ollama_par_defaut():
    model = build_model("ollama", "mistral:7b")
    assert type(model).__name__ == "ChatOllama"
    assert hasattr(model, "bind_tools")


@pytest.mark.parametrize("provider,classe,var", [
    ("anthropic", "ChatAnthropic", "ANTHROPIC_API_KEY"),
    ("openai", "ChatOpenAI", "OPENAI_API_KEY"),
    ("google_genai", "ChatGoogleGenerativeAI", "GOOGLE_API_KEY"),
])
def test_fournisseurs_cloud(provider, classe, var, monkeypatch):
    pytest.importorskip({"anthropic": "langchain_anthropic", "openai": "langchain_openai",
                         "google_genai": "langchain_google_genai"}[provider])
    monkeypatch.setenv(var, "cle-de-test")
    assert type(build_model(provider, "modele-test")).__name__ == classe


def test_cle_manquante_message_clair(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY manquante"):
        build_model("anthropic", "claude-sonnet-5")


def test_fournisseur_inconnu():
    with pytest.raises(SystemExit, match="LLM_PROVIDER inconnu"):
        build_model("mistral-cloud", "x")


def test_ollama_contexte_elargi():
    assert build_model("ollama", "mistral:7b").num_ctx == 8192
