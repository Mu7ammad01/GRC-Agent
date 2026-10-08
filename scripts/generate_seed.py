"""Génère les données fictives de la Banque Exemple Luxembourg (BEL).

Sorties (déterministes, régénérables avec `make seed`) :
  - db/02_seed.sql   : INSERT pour PostgreSQL
  - data/seed/*.csv  : mêmes données en CSV

Toutes les données sont fictives. Les références réglementaires (articles DORA,
circulaire CSSF 12/552, règlement CSSF 12-02, lois luxembourgeoises) servent de
cadre réaliste ; un article laissé à None reste à vérifier dans le texte source.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# Référentiels
# --------------------------------------------------------------------------

BUSINESS_UNITS = [
    # id, nom, ligne de défense
    ("RET", "Banque de détail", 1),
    ("PRI", "Banque privée", 1),
    ("TRE", "Trésorerie", 1),
    ("OPS", "Opérations", 1),
    ("DSI", "Direction des systèmes d'information", 1),
    ("RH", "Ressources humaines", 1),
    ("RSK", "Direction des risques", 2),
    ("CMP", "Conformité", 2),
    ("AUD", "Audit interne", 3),
]

USERS = [
    # id, nom, rôle, unité
    ("u.dupont", "Claire Dupont", "risk_manager", "RSK"),
    ("u.weber", "Marc Weber", "compliance_officer", "CMP"),
    ("u.schmit", "Paul Schmit", "metier", "DSI"),
    ("u.muller", "Anne Muller", "metier", "RET"),
    ("u.hoffmann", "Luc Hoffmann", "cro", "RSK"),
    ("u.kieffer", "Sophie Kieffer", "cco", "CMP"),
    ("u.reuter", "Jean Reuter", "auditeur", "AUD"),
]

RISK_CATEGORIES = [
    # Risque opérationnel : 7 catégories d'événements de Bâle II
    ("OP-FI", "Fraude interne", "operationnel"),
    ("OP-FE", "Fraude externe", "operationnel"),
    ("OP-RH", "Pratiques en matière d'emploi et sécurité au travail", "operationnel"),
    ("OP-CLI", "Clients, produits et pratiques commerciales", "operationnel"),
    ("OP-DOM", "Dommages aux actifs corporels", "operationnel"),
    ("OP-SYS", "Interruption d'activité et dysfonctionnement des systèmes", "operationnel"),
    ("OP-EXE", "Exécution, livraison et gestion des processus", "operationnel"),
    # Risque TIC (DORA)
    ("TIC-CYB", "Cybersécurité", "tic"),
    ("TIC-TIERS", "Risque lié aux prestataires tiers de services TIC", "tic"),
    ("TIC-DISP", "Disponibilité et continuité des TIC", "tic"),
    ("TIC-DATA", "Intégrité et confidentialité des données", "tic"),
    # Risque de conformité (catégories du support Compliance Fundamentals)
    ("CO-BC", "Blanchiment de capitaux et financement du terrorisme", "conformite"),
    ("CO-SAN", "Sanctions financières internationales", "conformite"),
    ("CO-JUR", "Risque juridique et réglementaire", "conformite"),
    ("CO-REP", "Risque de réputation", "conformite"),
]

RISK_APPETITE = [
    # famille, score résiduel max (V x I), énoncé
    ("operationnel", 12, "La BEL accepte un risque opérationnel résiduel modéré, sans perte unitaire supérieure à 500 000 EUR."),
    ("tic", 9, "La BEL n'accepte aucun risque TIC résiduel élevé sur ses fonctions critiques ou importantes."),
    ("conformite", 6, "La BEL a une tolérance faible au risque de conformité, et nulle en matière de sanctions et de blanchiment."),
]

# --------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------

CONTROLS = [
    # id, titre, description, type, nature, fréquence, unité, efficacité, dernier test
    ("C-001", "EDR sur serveurs et postes", "Détection et blocage des comportements malveillants sur tous les terminaux.", "detectif", "automatique", "continu", "DSI", "efficace", "2026-06-15"),
    ("C-002", "Sauvegardes immuables hors ligne", "Sauvegarde quotidienne des systèmes critiques sur un support non modifiable et déconnecté.", "preventif", "automatique", "quotidien", "DSI", "partiel", "2026-05-20"),
    ("C-003", "Gestion des correctifs de sécurité", "Application des correctifs critiques sous 30 jours selon la criticité des actifs.", "preventif", "semi_automatique", "mensuel", "DSI", "partiel", "2026-07-01"),
    ("C-004", "Authentification multifacteur", "MFA obligatoire pour l'accès distant, la messagerie et les applications critiques.", "preventif", "automatique", "continu", "DSI", "efficace", "2026-04-10"),
    ("C-005", "Filtrage de la messagerie", "Analyse des pièces jointes et des liens, blocage des domaines usurpés.", "preventif", "automatique", "continu", "DSI", "efficace", "2026-03-02"),
    ("C-006", "Sensibilisation à la sécurité", "Formation annuelle et campagnes trimestrielles d'hameçonnage simulé.", "preventif", "manuel", "trimestriel", "RH", "partiel", "2026-06-30"),
    ("C-007", "Gestion des accès à privilèges (PAM)", "Coffre-fort des comptes administrateurs, sessions enregistrées.", "preventif", "automatique", "continu", "DSI", "efficace", "2026-05-05"),
    ("C-008", "Revue périodique des droits d'accès", "Recertification trimestrielle des habilitations par les responsables.", "detectif", "manuel", "trimestriel", "DSI", "inefficace", "2026-07-15"),
    ("C-009", "Supervision de sécurité (SOC)", "Corrélation des journaux et traitement des alertes de sécurité 24/7.", "detectif", "automatique", "continu", "DSI", "efficace", "2026-06-01"),
    ("C-010", "Segmentation réseau", "Cloisonnement des zones critiques et filtrage des flux entre zones.", "preventif", "automatique", "continu", "DSI", "efficace", "2026-02-14"),
    ("C-011", "Stratégie de sortie des prestataires TIC critiques", "Plan documenté de réversibilité pour chaque prestataire critique.", "correctif", "manuel", "annuel", "DSI", "non_teste", None),
    ("C-012", "Suivi des niveaux de service des prestataires", "Revue mensuelle des SLA et des incidents des prestataires TIC.", "detectif", "manuel", "mensuel", "DSI", "efficace", "2026-08-31"),
    ("C-013", "Registre d'information des accords TIC", "Tenue du registre des contrats avec les prestataires de services TIC.", "detectif", "manuel", "trimestriel", "DSI", "partiel", "2026-06-30"),
    ("C-014", "Revue juridique des contrats TIC", "Vérification des clauses obligatoires avant signature ou renouvellement.", "preventif", "manuel", "evenementiel", "CMP", "partiel", "2026-05-12"),
    ("C-015", "Plan de continuité d'activité testé", "PCA couvrant les fonctions critiques, testé chaque année.", "correctif", "manuel", "annuel", "RSK", "efficace", "2025-11-20"),
    ("C-016", "Site de secours informatique", "Reprise des systèmes critiques sur un second centre de données.", "correctif", "automatique", "continu", "DSI", "efficace", "2025-11-20"),
    ("C-017", "Supervision des systèmes 24/7", "Surveillance de la disponibilité et des performances des applications.", "detectif", "automatique", "continu", "DSI", "efficace", "2026-07-01"),
    ("C-018", "Tests de restauration des sauvegardes", "Restauration trimestrielle d'un échantillon de systèmes critiques.", "detectif", "manuel", "trimestriel", "DSI", "inefficace", "2026-06-10"),
    ("C-019", "Prévention des fuites de données (DLP)", "Blocage des envois de données sensibles hors de la banque.", "preventif", "automatique", "continu", "DSI", "partiel", "2026-04-22"),
    ("C-020", "Classification des informations", "Étiquetage des documents selon leur niveau de confidentialité.", "preventif", "manuel", "annuel", "CMP", "partiel", "2026-01-15"),
    ("C-021", "Politique d'usage de l'IA générative", "Règles d'usage et liste des outils d'IA autorisés.", "preventif", "manuel", "annuel", "CMP", "non_teste", None),
    ("C-022", "Double validation (quatre yeux)", "Toute opération sensible est validée par une seconde personne.", "preventif", "manuel", "continu", "OPS", "efficace", "2026-05-30"),
    ("C-023", "Piste d'audit des modifications", "Journalisation des modifications de données de référence.", "detectif", "automatique", "continu", "DSI", "efficace", "2026-03-18"),
    ("C-024", "Séparation des tâches", "Incompatibilités de rôles paramétrées dans les applications.", "preventif", "semi_automatique", "continu", "OPS", "efficace", "2026-04-08"),
    ("C-025", "Rapprochements comptables quotidiens", "Rapprochement des comptes de passage et des comptes nostro.", "detectif", "manuel", "quotidien", "OPS", "efficace", "2026-08-29"),
    ("C-026", "Rappel de confirmation des virements inhabituels", "Contre-appel sur un numéro connu avant exécution.", "preventif", "manuel", "evenementiel", "OPS", "partiel", "2026-07-20"),
    ("C-027", "Scoring des transactions par carte", "Détection en temps réel des transactions frauduleuses.", "detectif", "automatique", "continu", "RET", "efficace", "2026-06-12"),
    ("C-028", "Vérification électronique de l'identité", "Contrôle de l'authenticité des pièces d'identité à l'ouverture.", "preventif", "semi_automatique", "evenementiel", "RET", "efficace", "2026-05-25"),
    ("C-029", "Due diligence KYC à l'entrée en relation", "Identification du client et du bénéficiaire effectif, cotation du risque.", "preventif", "manuel", "evenementiel", "CMP", "partiel", "2026-07-08"),
    ("C-030", "Suivi des réclamations clients", "Enregistrement, délai de réponse et analyse des causes.", "detectif", "manuel", "mensuel", "RET", "efficace", "2026-08-05"),
    ("C-031", "Test d'adéquation MiFID II", "Évaluation de l'adéquation du produit au profil du client.", "preventif", "semi_automatique", "evenementiel", "PRI", "efficace", "2026-06-18"),
    ("C-032", "Plan de succession des postes clés", "Identification de remplaçants pour les fonctions critiques.", "correctif", "manuel", "annuel", "RH", "non_teste", None),
    ("C-033", "Gestion des changements", "Validation, tests de non-régression et retour arrière des mises en production.", "preventif", "manuel", "evenementiel", "DSI", "partiel", "2026-07-28"),
    ("C-034", "Revue périodique des dossiers KYC", "Mise à jour des dossiers selon le niveau de risque du client.", "detectif", "manuel", "mensuel", "CMP", "inefficace", "2026-08-15"),
    ("C-035", "Surveillance des transactions (scénarios AML)", "Génération d'alertes sur les opérations atypiques.", "detectif", "automatique", "continu", "CMP", "efficace", "2026-05-14"),
    ("C-036", "Traitement et escalade des alertes AML", "Analyse des alertes et escalade au responsable du contrôle (RC).", "detectif", "manuel", "quotidien", "CMP", "inefficace", "2026-08-20"),
    ("C-037", "Déclaration à la CRF via goAML", "Procédure de déclaration des opérations suspectes à la Cellule de renseignement financier.", "correctif", "manuel", "evenementiel", "CMP", "efficace", "2026-03-10"),
    ("C-038", "Filtrage des listes de sanctions", "Filtrage des clients et des paiements contre les listes UE, ONU et nationales.", "preventif", "automatique", "continu", "CMP", "efficace", "2026-06-25"),
    ("C-039", "Veille réglementaire", "Identification des nouveaux textes et suivi des plans de mise en conformité.", "detectif", "manuel", "mensuel", "CMP", "partiel", "2026-07-31"),
    ("C-040", "Canal d'alerte interne confidentiel", "Dispositif de signalement protégeant l'identité du lanceur d'alerte.", "detectif", "manuel", "continu", "CMP", "efficace", "2026-02-20"),
]

# --------------------------------------------------------------------------
# Risques : id, titre, description, catégorie, processus, unité,
#           V brute, I brut, V résiduelle, I résiduel, contrôles
# --------------------------------------------------------------------------

RISKS = [
    ("R-001", "Rançongiciel sur le SI central", "Chiffrement des serveurs du système bancaire central rendant les services indisponibles.", "TIC-CYB", "Exploitation SI", "DSI", 4, 5, 2, 5, ["C-001", "C-002", "C-003", "C-009", "C-010"]),
    ("R-002", "Hameçonnage ciblé des collaborateurs", "Vol d'identifiants par des courriels frauduleux ciblant les collaborateurs.", "TIC-CYB", "Messagerie", "DSI", 5, 4, 3, 3, ["C-004", "C-005", "C-006"]),
    ("R-003", "Compromission d'un compte à privilèges", "Prise de contrôle d'un compte administrateur permettant des actions étendues sur le SI.", "TIC-CYB", "Administration SI", "DSI", 3, 5, 2, 4, ["C-004", "C-007", "C-008", "C-009"]),
    ("R-004", "Défaillance du prestataire cloud de la banque en ligne", "Indisponibilité durable ou faillite du prestataire hébergeant la banque en ligne.", "TIC-TIERS", "Banque en ligne", "DSI", 3, 5, 2, 5, ["C-011", "C-012", "C-013"]),
    ("R-005", "Clauses contractuelles TIC incomplètes", "Contrats TIC sans droits d'audit, localisation des données ou stratégie de sortie.", "TIC-TIERS", "Achats TIC", "DSI", 4, 3, 3, 3, ["C-013", "C-014"]),
    ("R-006", "Concentration sur un fournisseur TIC unique", "Dépendance de plusieurs fonctions critiques à un même fournisseur.", "TIC-TIERS", "Achats TIC", "DSI", 3, 4, 3, 3, ["C-011", "C-013"]),
    ("R-007", "Indisponibilité prolongée du système de paiement", "Arrêt du système de paiement au-delà de la durée maximale tolérable.", "TIC-DISP", "Paiements", "OPS", 3, 5, 2, 4, ["C-015", "C-016", "C-017"]),
    ("R-008", "Échec de restauration des sauvegardes", "Impossibilité de restaurer les données après un incident majeur.", "TIC-DISP", "Exploitation SI", "DSI", 3, 5, 2, 5, ["C-002", "C-018"]),
    ("R-009", "Fuite de données clients par un collaborateur", "Exfiltration volontaire ou accidentelle de données clients.", "TIC-DATA", "Gestion des données", "DSI", 3, 5, 2, 4, ["C-008", "C-019", "C-020"]),
    ("R-010", "Usage non encadré d'outils d'IA générative", "Saisie de données confidentielles dans des outils d'IA non autorisés (Shadow AI).", "TIC-DATA", "Postes de travail", "DSI", 4, 4, 3, 3, ["C-006", "C-019", "C-021"]),
    ("R-011", "Modification non autorisée de données de référence", "Altération des coordonnées bancaires ou des plafonds clients.", "TIC-DATA", "Données de référence", "OPS", 2, 4, 2, 3, ["C-022", "C-023"]),
    ("R-012", "Détournement de fonds par un collaborateur", "Virements frauduleux initiés en interne.", "OP-FI", "Paiements", "OPS", 2, 5, 1, 4, ["C-022", "C-024", "C-025"]),
    ("R-013", "Fraude au président", "Exécution d'un faux virement sur instruction usurpant un dirigeant.", "OP-FE", "Paiements", "OPS", 4, 4, 2, 3, ["C-006", "C-026"]),
    ("R-014", "Fraude à la carte bancaire", "Utilisation frauduleuse de cartes de clients.", "OP-FE", "Cartes", "RET", 4, 3, 3, 2, ["C-027"]),
    ("R-015", "Usurpation d'identité à l'ouverture de compte", "Ouverture de compte avec de faux documents.", "OP-FE", "Entrée en relation", "RET", 3, 4, 2, 3, ["C-028", "C-029"]),
    ("R-016", "Erreur de saisie d'ordres de paiement", "Montant, bénéficiaire ou date erronés dans un ordre de paiement.", "OP-EXE", "Paiements", "OPS", 4, 3, 3, 2, ["C-022", "C-025"]),
    ("R-017", "Retard de traitement des réclamations", "Réponses aux clients au-delà des délais réglementaires.", "OP-CLI", "Relation client", "RET", 3, 3, 3, 2, ["C-030"]),
    ("R-018", "Vente de produits inadaptés au profil client", "Conseil en investissement non adapté au profil du client.", "OP-CLI", "Conseil en investissement", "PRI", 3, 4, 2, 3, ["C-031"]),
    ("R-019", "Départ de collaborateurs clés en cybersécurité", "Perte de compétences critiques difficiles à remplacer.", "OP-RH", "Gestion des talents", "RH", 3, 3, 3, 3, ["C-032"]),
    ("R-020", "Sinistre sur le bâtiment principal", "Incendie ou inondation rendant le siège inaccessible.", "OP-DOM", "Logistique", "OPS", 1, 5, 1, 4, ["C-015", "C-016"]),
    ("R-021", "Panne d'une application métier critique", "Indisponibilité de l'application de gestion des crédits.", "OP-SYS", "Crédit", "DSI", 3, 4, 2, 3, ["C-017", "C-033"]),
    ("R-022", "Changement applicatif mal testé en production", "Régression introduite lors d'une mise en production.", "OP-SYS", "Gestion des changements", "DSI", 4, 3, 3, 3, ["C-033"]),
    ("R-023", "Défaut de vigilance à l'entrée en relation", "Dossiers clients incomplets ou cotation de risque erronée.", "CO-BC", "Entrée en relation", "CMP", 4, 5, 2, 4, ["C-028", "C-029", "C-034"]),
    ("R-024", "Alertes de surveillance des transactions non traitées", "Accumulation d'alertes AML non analysées dans les délais.", "CO-BC", "Surveillance des transactions", "CMP", 4, 5, 3, 3, ["C-035", "C-036"]),
    ("R-025", "Défaut de déclaration d'opération suspecte", "Opération suspecte non déclarée à la CRF.", "CO-BC", "Déclarations CRF", "CMP", 2, 5, 1, 5, ["C-036", "C-037"]),
    ("R-026", "Opération avec une personne sanctionnée", "Paiement au profit d'une personne visée par des sanctions.", "CO-SAN", "Filtrage", "CMP", 3, 5, 1, 5, ["C-038"]),
    ("R-027", "Retard de mise en conformité DORA", "Exigences DORA non couvertes à la date d'application.", "CO-JUR", "Veille réglementaire", "CMP", 4, 4, 2, 3, ["C-013", "C-039"]),
    ("R-028", "Violation du secret professionnel", "Divulgation d'informations clients en violation de l'article 41 de la loi de 1993.", "CO-JUR", "Gestion des données", "CMP", 2, 5, 1, 5, ["C-019", "C-020"]),
    ("R-029", "Défaillance du dispositif d'alerte interne", "Signalements non traités ou identité du lanceur d'alerte exposée.", "CO-REP", "Éthique", "CMP", 2, 4, 2, 3, ["C-040"]),
    ("R-030", "Atteinte à la réputation après un incident médiatisé", "Perte de confiance des clients après un incident rendu public.", "CO-REP", "Communication de crise", "RSK", 3, 4, 2, 4, ["C-015", "C-030"]),
]

# --------------------------------------------------------------------------
# Réglementation
# --------------------------------------------------------------------------

REGULATIONS = [
    # id, nom court, titre, niveau, référence, url
    ("REG-DORA", "DORA", "Règlement sur la résilience opérationnelle numérique du secteur financier", 1, "Règlement (UE) 2022/2554", "https://eur-lex.europa.eu/eli/reg/2022/2554/oj"),
    ("REG-AIACT", "AI Act", "Règlement établissant des règles harmonisées concernant l'intelligence artificielle", 1, "Règlement (UE) 2024/1689", "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    ("REG-L1993", "Loi de 1993", "Loi du 5 avril 1993 relative au secteur financier", 3, "Loi du 5 avril 1993, telle que modifiée", None),
    ("REG-L2004", "Loi LBC/FT", "Loi du 12 novembre 2004 relative à la lutte contre le blanchiment et contre le financement du terrorisme", 3, "Loi du 12 novembre 2004, telle que modifiée", None),
    ("REG-C12552", "CSSF 12/552", "Administration centrale, gouvernance interne et gestion des risques", 4, "Circulaire CSSF 12/552, telle que modifiée (dont 24/860)", None),
    ("REG-R1202", "Règlement CSSF 12-02", "Lutte contre le blanchiment et contre le financement du terrorisme", 4, "Règlement CSSF n° 12-02, tel que modifié par le règlement 20-05", None),
    ("REG-POL-PSSI", "PSSI BEL", "Politique de sécurité de l'information de la BEL", 5, "data/policies/politique_securite_information.md", None),
    ("REG-POL-TIERS", "Politique prestataires TIC", "Politique de gestion des prestataires de services TIC de la BEL", 5, "data/policies/politique_prestataires_tic.md", None),
    ("REG-POL-INC", "Politique incidents", "Politique de gestion des incidents de la BEL", 5, "data/policies/politique_gestion_incidents.md", None),
]

OBLIGATIONS = [
    # id, réglementation, article, résumé, unité responsable, contrôles
    ("O-001", "REG-DORA", "Art. 5", "L'organe de direction définit, approuve et supervise le cadre de gestion du risque lié aux TIC et en porte la responsabilité finale.", "RSK", ["C-039"]),
    ("O-002", "REG-DORA", "Art. 6", "Disposer d'un cadre de gestion du risque TIC solide, complet et documenté, réexaminé au moins une fois par an.", "RSK", ["C-039"]),
    ("O-003", "REG-DORA", "Art. 8", "Identifier, classer et documenter les fonctions métiers, les actifs informationnels et TIC et leurs dépendances.", "DSI", ["C-013", "C-020"]),
    ("O-004", "REG-DORA", "Art. 9", "Mettre en place des politiques de protection et de prévention : contrôle d'accès, authentification forte, gestion des correctifs.", "DSI", ["C-003", "C-004", "C-007", "C-010"]),
    ("O-005", "REG-DORA", "Art. 10", "Détecter rapidement les activités anormales, y compris les problèmes de performance et les incidents TIC.", "DSI", ["C-001", "C-009", "C-017"]),
    ("O-006", "REG-DORA", "Art. 11", "Disposer d'une politique de continuité des activités TIC et de plans de réponse et de rétablissement testés.", "RSK", ["C-015", "C-016"]),
    ("O-007", "REG-DORA", "Art. 12", "Définir des politiques de sauvegarde et des procédures de restauration et de rétablissement testées.", "DSI", ["C-002", "C-018"]),
    ("O-008", "REG-DORA", "Art. 13", "Tirer les enseignements des incidents et former le personnel et l'organe de direction à la sécurité des TIC.", "RH", ["C-006"]),
    ("O-009", "REG-DORA", "Art. 17", "Définir et mettre en œuvre un processus de gestion des incidents liés aux TIC pour les détecter, les gérer et les notifier.", "DSI", ["C-009", "C-017"]),
    ("O-010", "REG-DORA", "Art. 18", "Classer les incidents liés aux TIC selon les critères réglementaires pour déterminer les incidents majeurs.", "RSK", []),
    ("O-011", "REG-DORA", "Art. 19", "Notifier les incidents majeurs liés aux TIC à l'autorité compétente (CSSF) dans les délais prévus.", "RSK", []),
    ("O-012", "REG-DORA", "Art. 24", "Établir et maintenir un programme de tests de résilience opérationnelle numérique.", "DSI", ["C-015"]),
    ("O-013", "REG-DORA", "Art. 28, par. 3", "Tenir un registre d'informations sur tous les accords contractuels avec des prestataires tiers de services TIC.", "DSI", ["C-013"]),
    ("O-014", "REG-DORA", "Art. 28", "Gérer le risque lié aux prestataires tiers de services TIC selon une stratégie adoptée par l'organe de direction.", "DSI", ["C-011", "C-012"]),
    ("O-015", "REG-DORA", "Art. 30", "Inclure les dispositions contractuelles clés : niveaux de service, localisation des données, droits d'audit, stratégie de sortie.", "CMP", ["C-014"]),
    ("O-016", "REG-C12552", None, "Disposer d'une fonction compliance permanente et indépendante, dirigée par un Chief Compliance Officer.", "CMP", ["C-039"]),
    ("O-017", "REG-C12552", "Art. 94", "Maintenir un dispositif d'alerte interne garantissant la confidentialité de l'identité des personnes qui signalent.", "CMP", ["C-040"]),
    ("O-018", "REG-C12552", None, "La direction autorisée rend compte au moins une fois par an au conseil d'administration de l'activité de la fonction compliance.", "CMP", []),
    ("O-019", "REG-C12552", None, "Établir un plan de contrôle compliance annuel (Compliance Monitoring Plan) fondé sur les risques.", "CMP", ["C-039"]),
    ("O-020", "REG-C12552", None, "Évaluer le risque de conformité avant le lancement de nouveaux produits, activités ou systèmes.", "CMP", []),
    ("O-021", "REG-R1202", "Art. 40", "Désigner un responsable du respect des obligations LBC/FT (RR) et un responsable du contrôle (RC).", "CMP", []),
    ("O-022", "REG-R1202", "Art. 42", "Le RC contrôle la qualité des contrôles LBC/FT de 1re ligne, organise la formation et rend compte par écrit à la direction.", "CMP", ["C-006", "C-036"]),
    ("O-023", "REG-L2004", "Art. 5", "Déclarer sans délai à la Cellule de renseignement financier toute opération suspecte (via goAML).", "CMP", ["C-036", "C-037"]),
    ("O-024", "REG-L2004", "Art. 3", "Appliquer des mesures de vigilance à l'égard de la clientèle à l'entrée en relation et de façon continue.", "CMP", ["C-028", "C-029", "C-034"]),
    ("O-025", "REG-L1993", "Art. 41", "Respecter le secret professionnel sur les informations confiées par les clients.", "CMP", ["C-019", "C-020"]),
]

COMPLIANCE_ACTIONS = [
    # id, titre, obligation, responsable, échéance, statut
    ("CA-001", "Formaliser la procédure de classification des incidents TIC (DORA art. 18)", "O-010", "u.dupont", "2026-11-30", "en_cours"),
    ("CA-002", "Mettre en place le processus de notification des incidents majeurs à la CSSF", "O-011", "u.dupont", "2026-10-31", "en_retard"),
    ("CA-003", "Compléter le registre d'information des accords TIC", "O-013", "u.schmit", "2026-12-15", "en_cours"),
    ("CA-004", "Ajouter les clauses d'audit et de sortie aux 6 contrats TIC critiques", "O-015", "u.weber", "2027-01-31", "a_faire"),
    ("CA-005", "Rédiger le rapport annuel compliance au conseil d'administration", "O-018", "u.kieffer", "2027-02-28", "a_faire"),
    ("CA-006", "Créer le comité d'approbation des nouveaux produits", "O-020", "u.kieffer", "2026-12-31", "a_faire"),
    ("CA-007", "Résorber l'arriéré d'alertes AML de plus de 30 jours", "O-023", "u.weber", "2026-10-15", "en_retard"),
    ("CA-008", "Formaliser la désignation du RR et du RC LBC/FT", "O-021", "u.kieffer", "2026-11-15", "termine"),
]

INCIDENTS = [
    # id, date, titre, description, catégorie, risque, perte brute, récupéré, majeur TIC, statut
    ("I-001", "2026-01-12", "Campagne d'hameçonnage réussie", "Trois collaborateurs ont saisi leurs identifiants sur un faux portail ; comptes bloqués sous 2 heures.", "TIC-CYB", "R-002", 0, 0, False, "clos"),
    ("I-002", "2026-01-27", "Erreur de saisie sur un virement", "Virement de 48 000 EUR envoyé au mauvais bénéficiaire.", "OP-EXE", "R-016", 48000, 41000, False, "clos"),
    ("I-003", "2026-02-09", "Panne du système de paiement", "Arrêt de 5 heures du système de paiement après une mise à jour du prestataire.", "TIC-DISP", "R-007", 22000, 0, True, "clos"),
    ("I-004", "2026-02-21", "Fraude au président", "Faux virement de 135 000 EUR demandé par un courriel usurpant le directeur financier.", "OP-FE", "R-013", 135000, 60000, False, "clos"),
    ("I-005", "2026-03-04", "Fraude carte sur un commerçant en ligne", "Série de transactions frauduleuses détectées par le scoring.", "OP-FE", "R-014", 18500, 12000, False, "clos"),
    ("I-006", "2026-03-18", "Retard de revue KYC", "120 dossiers à risque élevé non revus dans les délais.", "CO-BC", "R-023", 0, 0, False, "en_analyse"),
    ("I-007", "2026-04-02", "Échec d'un test de restauration", "La restauration de la base clients a échoué lors du test trimestriel.", "TIC-DISP", "R-008", 0, 0, False, "en_analyse"),
    ("I-008", "2026-04-16", "Données clients collées dans un outil d'IA public", "Un conseiller a soumis un extrait de portefeuille à un chatbot public.", "TIC-DATA", "R-010", 0, 0, False, "clos"),
    ("I-009", "2026-04-29", "Régression après mise en production", "Calcul erroné des intérêts sur 340 crédits pendant 2 jours.", "OP-SYS", "R-022", 9500, 0, False, "clos"),
    ("I-010", "2026-05-11", "Accumulation d'alertes AML", "Plus de 400 alertes de plus de 30 jours en attente d'analyse.", "CO-BC", "R-024", 0, 0, False, "ouvert"),
    ("I-011", "2026-05-23", "Indisponibilité de la banque en ligne", "Panne de 9 heures chez le prestataire cloud ; 30 % des clients affectés.", "TIC-TIERS", "R-004", 64000, 25000, True, "clos"),
    ("I-012", "2026-06-05", "Compte administrateur non désactivé", "Compte d'un prestataire parti actif depuis 4 mois, sans usage constaté.", "TIC-CYB", "R-003", 0, 0, False, "clos"),
    ("I-013", "2026-06-19", "Réclamations en retard", "45 réclamations traitées au-delà du délai d'un mois.", "OP-CLI", "R-017", 3000, 0, False, "clos"),
    ("I-014", "2026-07-01", "Contrat TIC sans clause de sortie", "Renouvellement d'un contrat critique sans stratégie de sortie.", "TIC-TIERS", "R-005", 0, 0, False, "en_analyse"),
    ("I-015", "2026-07-14", "Tentative de rançongiciel bloquée", "Charge malveillante bloquée par l'EDR sur un serveur de fichiers.", "TIC-CYB", "R-001", 0, 0, False, "clos"),
    ("I-016", "2026-07-30", "Ouverture de compte avec faux documents", "Compte ouvert avec un passeport falsifié, détecté à la revue.", "OP-FE", "R-015", 7200, 0, False, "clos"),
    ("I-017", "2026-08-12", "Correctif critique non appliqué", "Vulnérabilité critique sur le VPN non corrigée après 45 jours.", "TIC-CYB", "R-001", 0, 0, False, "ouvert"),
    ("I-018", "2026-08-25", "Faux positif de sanctions bloquant un paiement", "Paiement bloqué 3 jours par homonymie ; réclamation du client.", "CO-SAN", "R-026", 1500, 0, False, "clos"),
    ("I-019", "2026-09-08", "Erreur de rapprochement", "Écart de 12 000 EUR sur un compte nostro, régularisé.", "OP-EXE", "R-016", 12000, 12000, False, "clos"),
    ("I-020", "2026-09-21", "Fuite de données par courriel", "Envoi par erreur d'un fichier de 800 clients à un tiers.", "TIC-DATA", "R-009", 15000, 0, False, "en_analyse"),
]

KRIS = [
    # id, nom, unité, risque, plus haut = pire, seuil d'alerte, seuil d'appétit, valeurs jan. à sept. 2026
    ("K-01", "Disponibilité des systèmes critiques", "%", "R-007", False, 99.7, 99.5, [99.9, 99.4, 99.8, 99.9, 99.6, 99.8, 99.9, 99.9, 99.8]),
    ("K-02", "Incidents TIC majeurs dans le mois", "nombre", "R-001", True, 0, 1, [0, 1, 0, 0, 1, 0, 0, 0, 0]),
    ("K-03", "Correctifs critiques en retard de plus de 30 jours", "nombre", "R-001", True, 5, 10, [3, 4, 6, 5, 7, 9, 8, 12, 9]),
    ("K-04", "Collaborateurs formés à la sécurité", "%", "R-002", False, 90, 80, [72, 75, 81, 84, 86, 88, 89, 91, 92]),
    ("K-05", "Alertes AML non traitées depuis plus de 30 jours", "nombre", "R-024", True, 20, 50, [35, 60, 120, 260, 410, 380, 290, 150, 70]),
    ("K-06", "Dossiers KYC à risque élevé en retard de revue", "%", "R-023", True, 5, 10, [4, 6, 11, 9, 8, 7, 6, 6, 5]),
    ("K-07", "Prestataires TIC critiques sans clause d'audit", "%", "R-005", True, 5, 10, [33, 33, 33, 25, 25, 25, 17, 17, 17]),
    ("K-08", "Pertes opérationnelles brutes du mois", "kEUR", "R-016", True, 100, 250, [48, 157, 18.5, 9.5, 64, 3, 7.2, 1.5, 27]),
]

# --------------------------------------------------------------------------
# Écriture
# --------------------------------------------------------------------------


def sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def tables() -> dict[str, tuple[list[str], list[tuple]]]:
    """Retourne {table: (colonnes, lignes)} dans l'ordre d'insertion."""
    t: dict[str, tuple[list[str], list[tuple]]] = {}
    t["business_units"] = (["id", "name", "line"], BUSINESS_UNITS)
    t["users"] = (["id", "full_name", "role", "unit_id"], USERS)
    t["risk_categories"] = (["id", "name", "family"], RISK_CATEGORIES)
    t["risk_appetite"] = (
        ["family", "max_residual_score", "statement", "approved_by", "approved_on"],
        [(f, s, st, "Conseil d'administration", "2026-01-29") for f, s, st in RISK_APPETITE],
    )
    t["controls"] = (
        ["id", "title", "description", "control_type", "nature", "frequency", "owner_unit_id", "effectiveness", "last_test"],
        CONTROLS,
    )
    t["risks"] = (
        ["id", "title", "description", "category_id", "process", "owner_unit_id",
         "inherent_likelihood", "inherent_impact", "residual_likelihood", "residual_impact", "status", "last_review"],
        [r[:10] + ("actif", "2026-06-30") for r in RISKS],
    )
    t["risk_controls"] = (["risk_id", "control_id"], [(r[0], c) for r in RISKS for c in r[10]])
    t["regulations"] = (["id", "short_name", "title", "norm_level", "reference", "url"], REGULATIONS)
    t["obligations"] = (["id", "regulation_id", "article", "summary", "owner_unit_id"], [o[:5] for o in OBLIGATIONS])
    t["obligation_controls"] = (["obligation_id", "control_id"], [(o[0], c) for o in OBLIGATIONS for c in o[5]])
    t["compliance_actions"] = (["id", "title", "obligation_id", "owner_id", "due_date", "status"], COMPLIANCE_ACTIONS)
    t["incidents"] = (
        ["id", "occurred_on", "title", "description", "category_id", "risk_id", "gross_loss_eur", "recovered_eur", "major_ict", "status"],
        INCIDENTS,
    )
    t["kris"] = (
        ["id", "name", "unit", "risk_id", "higher_is_worse", "warning_threshold", "appetite_threshold"],
        [k[:7] for k in KRIS],
    )
    t["kri_values"] = (
        ["kri_id", "period", "value"],
        [(k[0], date(2026, m + 1, 1).isoformat(), v) for k in KRIS for m, v in enumerate(k[7])],
    )
    return t


def main() -> None:
    data = tables()

    lines = [
        "-- Généré par scripts/generate_seed.py — ne pas modifier à la main.",
        "-- Données fictives de la Banque Exemple Luxembourg (BEL).",
        "BEGIN;",
    ]
    for name, (cols, rows) in data.items():
        lines.append(f"\n-- {name} ({len(rows)} lignes)")
        for row in rows:
            values = ", ".join(sql_value(v) for v in row)
            lines.append(f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({values});")
    lines.append("\nCOMMIT;\n")
    (ROOT / "db" / "02_seed.sql").write_text("\n".join(lines), encoding="utf-8")

    seed_dir = ROOT / "data" / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    for name, (cols, rows) in data.items():
        with open(seed_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)

    summary = ", ".join(f"{n}={len(r)}" for n, (_, r) in data.items())
    print(f"Données générées : {summary}")


if __name__ == "__main__":
    main()
