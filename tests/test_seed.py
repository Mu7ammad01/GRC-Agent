"""Tests des données fictives (sans base) et du schéma (avec PostgreSQL si DATABASE_URL est défini)."""
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("generate_seed", ROOT / "scripts" / "generate_seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


# ---------- Cohérence des données, sans base ----------

def test_volumes_du_jeu_de_donnees():
    assert len(seed.RISKS) == 30
    assert len(seed.CONTROLS) == 40
    assert len(seed.OBLIGATIONS) == 25
    assert len(seed.INCIDENTS) == 20
    assert len(seed.KRIS) == 8


def test_references_croisees():
    controls = {c[0] for c in seed.CONTROLS}
    risks = {r[0] for r in seed.RISKS}
    for r in seed.RISKS:
        assert set(r[10]) <= controls, r[0]
    for o in seed.OBLIGATIONS:
        assert set(o[5]) <= controls, o[0]
    for i in seed.INCIDENTS:
        assert i[5] in risks, i[0]


def test_risque_residuel_inferieur_au_brut():
    for r in seed.RISKS:
        assert r[8] * r[9] <= r[6] * r[7], r[0]


def test_pertes_mensuelles_coherentes_avec_les_incidents():
    """Le KRI K-08 (pertes brutes du mois, kEUR) doit refléter la base incidents."""
    k08 = next(k for k in seed.KRIS if k[0] == "K-08")[7]
    for month in range(1, 10):
        total = sum(i[6] for i in seed.INCIDENTS if int(i[1][5:7]) == month) / 1000
        assert abs(total - k08[month - 1]) < 0.01, month


def test_politique_piegee_presente():
    """La politique incidents contient l'injection utilisée pour la menace M2."""
    text = (ROOT / "data" / "policies" / "politique_gestion_incidents.md").read_text(encoding="utf-8")
    assert "assistants automatisés" in text


# ---------- Schéma, avec PostgreSQL ----------

DATABASE_URL = os.getenv("DATABASE_URL")
needs_db = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL non défini")


@pytest.fixture
def conn():
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(DATABASE_URL) as c:
        yield c
        c.rollback()


@needs_db
def test_risques_hors_appetit(conn):
    ids = {r[0] for r in conn.execute("SELECT id FROM v_risks_over_appetite").fetchall()}
    assert ids == {"R-001", "R-004", "R-008", "R-023", "R-024", "R-030"}


@needs_db
def test_journal_audit_en_ajout_seul(conn):
    psycopg = pytest.importorskip("psycopg")
    conn.execute("INSERT INTO audit_log (actor, event, hash) VALUES ('test', 'test', 'h')")
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("DELETE FROM audit_log")


@needs_db
def test_pas_d_auto_validation(conn):
    psycopg = pytest.importorskip("psycopg")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO pending_actions (requested_by, action, payload, status, decided_by) "
            "VALUES ('u.dupont', 'add_risk', '{}', 'validee', 'u.dupont')"
        )
