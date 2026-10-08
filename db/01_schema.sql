-- =====================================================================
-- GRC-Agent — schéma de la base GRC (PostgreSQL 16)
-- Banque Exemple Luxembourg (BEL) — données fictives
-- Cotations : vraisemblance et impact de 1 (faible) à 5 (très élevé),
-- score = vraisemblance x impact (1 à 25).
-- =====================================================================

-- ---------- Référentiels ----------

CREATE TABLE business_units (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    line        SMALLINT NOT NULL CHECK (line IN (1, 2, 3))   -- ligne de défense
);

CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    full_name   TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN
                  ('metier', 'risk_manager', 'compliance_officer', 'cro', 'cco', 'auditeur')),
    unit_id     TEXT NOT NULL REFERENCES business_units(id)
);

CREATE TABLE risk_categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    family      TEXT NOT NULL CHECK (family IN ('operationnel', 'tic', 'conformite'))
);

-- Appétit pour le risque : fixé par le conseil d'administration (niveau N3 pour l'agent)
CREATE TABLE risk_appetite (
    family              TEXT PRIMARY KEY CHECK (family IN ('operationnel', 'tic', 'conformite')),
    max_residual_score  SMALLINT NOT NULL CHECK (max_residual_score BETWEEN 1 AND 25),
    statement           TEXT NOT NULL,
    approved_by         TEXT NOT NULL,
    approved_on         DATE NOT NULL
);

-- ---------- Registre des risques et contrôles ----------

CREATE TABLE risks (
    id                    TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    description           TEXT NOT NULL,
    category_id           TEXT NOT NULL REFERENCES risk_categories(id),
    process               TEXT NOT NULL,
    owner_unit_id         TEXT NOT NULL REFERENCES business_units(id),
    inherent_likelihood   SMALLINT NOT NULL CHECK (inherent_likelihood BETWEEN 1 AND 5),
    inherent_impact       SMALLINT NOT NULL CHECK (inherent_impact BETWEEN 1 AND 5),
    residual_likelihood   SMALLINT NOT NULL CHECK (residual_likelihood BETWEEN 1 AND 5),
    residual_impact       SMALLINT NOT NULL CHECK (residual_impact BETWEEN 1 AND 5),
    status                TEXT NOT NULL DEFAULT 'actif' CHECK (status IN ('actif', 'en_revue', 'clos')),
    last_review           DATE NOT NULL,
    inherent_score        SMALLINT GENERATED ALWAYS AS (inherent_likelihood * inherent_impact) STORED,
    residual_score        SMALLINT GENERATED ALWAYS AS (residual_likelihood * residual_impact) STORED,
    CHECK (residual_likelihood * residual_impact <= inherent_likelihood * inherent_impact)
);

CREATE TABLE controls (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    control_type    TEXT NOT NULL CHECK (control_type IN ('preventif', 'detectif', 'correctif')),
    nature          TEXT NOT NULL CHECK (nature IN ('manuel', 'automatique', 'semi_automatique')),
    frequency       TEXT NOT NULL CHECK (frequency IN
                      ('continu', 'quotidien', 'hebdomadaire', 'mensuel', 'trimestriel', 'annuel', 'evenementiel')),
    owner_unit_id   TEXT NOT NULL REFERENCES business_units(id),
    effectiveness   TEXT NOT NULL CHECK (effectiveness IN ('efficace', 'partiel', 'inefficace', 'non_teste')),
    last_test       DATE
);

CREATE TABLE risk_controls (
    risk_id     TEXT REFERENCES risks(id) ON DELETE CASCADE,
    control_id  TEXT REFERENCES controls(id) ON DELETE CASCADE,
    PRIMARY KEY (risk_id, control_id)
);

-- ---------- Réglementation ----------

-- Pyramide des normes : du texte européen à la procédure interne
CREATE TABLE regulations (
    id          TEXT PRIMARY KEY,
    short_name  TEXT NOT NULL,
    title       TEXT NOT NULL,
    norm_level  SMALLINT NOT NULL CHECK (norm_level BETWEEN 1 AND 5),
    -- 1 = règlement UE, 2 = directive UE, 3 = loi luxembourgeoise,
    -- 4 = règlement ou circulaire CSSF, 5 = politique ou procédure interne
    reference   TEXT NOT NULL,
    url         TEXT
);

CREATE TABLE obligations (
    id              TEXT PRIMARY KEY,
    regulation_id   TEXT NOT NULL REFERENCES regulations(id),
    article         TEXT,              -- NULL si l'article exact reste à vérifier
    summary         TEXT NOT NULL,
    owner_unit_id   TEXT NOT NULL REFERENCES business_units(id)
);

CREATE TABLE obligation_controls (
    obligation_id   TEXT REFERENCES obligations(id) ON DELETE CASCADE,
    control_id      TEXT REFERENCES controls(id) ON DELETE CASCADE,
    PRIMARY KEY (obligation_id, control_id)
);

-- Plan d'action conformité
CREATE TABLE compliance_actions (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    obligation_id   TEXT REFERENCES obligations(id),
    owner_id        TEXT NOT NULL REFERENCES users(id),
    due_date        DATE NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('a_faire', 'en_cours', 'termine', 'en_retard'))
);

-- ---------- Incidents et indicateurs ----------

CREATE TABLE incidents (
    id              TEXT PRIMARY KEY,
    occurred_on     DATE NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    category_id     TEXT NOT NULL REFERENCES risk_categories(id),
    risk_id         TEXT REFERENCES risks(id),
    gross_loss_eur  NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (gross_loss_eur >= 0),
    recovered_eur   NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (recovered_eur >= 0),
    major_ict       BOOLEAN NOT NULL DEFAULT FALSE,     -- incident TIC majeur au sens de DORA
    status          TEXT NOT NULL CHECK (status IN ('ouvert', 'en_analyse', 'clos')),
    CHECK (recovered_eur <= gross_loss_eur)
);

CREATE TABLE kris (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    unit                TEXT NOT NULL,
    risk_id             TEXT NOT NULL REFERENCES risks(id),
    higher_is_worse     BOOLEAN NOT NULL,
    warning_threshold   NUMERIC NOT NULL,
    appetite_threshold  NUMERIC NOT NULL
);

CREATE TABLE kri_values (
    kri_id      TEXT REFERENCES kris(id) ON DELETE CASCADE,
    period      DATE NOT NULL,          -- premier jour du mois
    value       NUMERIC NOT NULL,
    PRIMARY KEY (kri_id, period)
);

-- ---------- Traçabilité de l'agent (utilisées à partir de la semaine 2) ----------

-- File des actions N2 en attente de validation humaine
CREATE TABLE pending_actions (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    requested_by    TEXT NOT NULL REFERENCES users(id),
    action          TEXT NOT NULL,
    payload         JSONB NOT NULL,
    status          TEXT NOT NULL DEFAULT 'en_attente' CHECK (status IN ('en_attente', 'validee', 'refusee')),
    decided_by      TEXT REFERENCES users(id),
    decided_at      TIMESTAMPTZ,
    CHECK (decided_by IS NULL OR decided_by <> requested_by)   -- pas d'auto-validation
);

-- Journal d'audit chaîné : chaque ligne contient l'empreinte de la précédente
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor           TEXT NOT NULL,
    event           TEXT NOT NULL,
    authority_level TEXT CHECK (authority_level IN ('N0', 'N1', 'N2', 'N3')),
    decision        TEXT CHECK (decision IN ('autorise', 'refuse', 'en_attente')),
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash       TEXT,
    hash            TEXT NOT NULL
);

-- Le journal est en ajout seul
CREATE FUNCTION forbid_audit_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log est en ajout seul';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_change();

-- ---------- Vues utiles à l'agent ----------

CREATE VIEW v_risks_over_appetite AS
SELECT r.id, r.title, c.family, r.residual_score, a.max_residual_score,
       r.owner_unit_id
FROM risks r
JOIN risk_categories c ON c.id = r.category_id
JOIN risk_appetite a   ON a.family = c.family
WHERE r.status <> 'clos'
  AND r.residual_score > a.max_residual_score;

CREATE VIEW v_kri_status AS
SELECT k.id, k.name, v.period, v.value, k.warning_threshold, k.appetite_threshold,
       CASE
         WHEN (k.higher_is_worse AND v.value > k.appetite_threshold)
           OR (NOT k.higher_is_worse AND v.value < k.appetite_threshold) THEN 'hors_appetit'
         WHEN (k.higher_is_worse AND v.value > k.warning_threshold)
           OR (NOT k.higher_is_worse AND v.value < k.warning_threshold) THEN 'alerte'
         ELSE 'normal'
       END AS status
FROM kris k
JOIN kri_values v ON v.kri_id = k.id;

CREATE VIEW v_obligations_without_effective_control AS
SELECT o.id, o.regulation_id, o.article, o.summary
FROM obligations o
WHERE NOT EXISTS (
    SELECT 1
    FROM obligation_controls oc
    JOIN controls c ON c.id = oc.control_id
    WHERE oc.obligation_id = o.id AND c.effectiveness = 'efficace'
);
