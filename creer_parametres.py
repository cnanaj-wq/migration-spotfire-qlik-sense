"""Crée le classeur de paramètres initial (parametres/parametres.xlsx).

À lancer une seule fois. Ensuite le classeur se modifie à la main dans Excel :
il pilote la génération des données, la sécurité par région (Spotfire puis
Section Access dans Qlik Sense) et les seuils d'alerte des indicateurs.
Le script refuse d'écraser un classeur existant.
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

CIBLE = Path(__file__).parent / "parametres" / "parametres.xlsx"

GENERAL = [
    ("Clé", "Valeur", "Description"),
    (
        "societe",
        "Orvane Distribution",
        "Nom de la société fictive affiché dans les titres",
    ),
    (
        "dernier_mois_clos",
        "2026-10",
        "Dernier mois de réel (AAAA-MM) ; au-delà : prévision",
    ),
    ("devise", "EUR", "Devise d'affichage"),
    (
        "domaine_utilisateurs",
        "orvane.example",
        "Domaine des comptes fictifs de la feuille Sécurité",
    ),
]

# ACCESS / USER.EMAIL / RÉGION reprennent le vocabulaire de la Section Access de Qlik Sense.
# RÉGION = * : toutes les régions.
SECURITE = [
    ("ACCESS", "USER.EMAIL", "Nom", "Profil", "Région"),
    (
        "ADMIN",
        "A_REMPLACER_PAR_TON_EMAIL_QLIK",
        "Administrateur du tenant",
        "Administrateur",
        "*",
    ),
    ("USER", "daf@orvane.example", "Claire Morel", "Direction financière", "*"),
    (
        "USER",
        "cdg.groupe@orvane.example",
        "Julien Faure",
        "Contrôle de gestion groupe",
        "*",
    ),
    (
        "USER",
        "cdg.idf@orvane.example",
        "Sophie Lambert",
        "Contrôle de gestion région",
        "Île-de-France",
    ),
    (
        "USER",
        "cdg.sudest@orvane.example",
        "Karim Benali",
        "Contrôle de gestion région",
        "Sud-Est",
    ),
    (
        "USER",
        "cdg.ouest@orvane.example",
        "Maëlle Le Goff",
        "Contrôle de gestion région",
        "Ouest",
    ),
    (
        "USER",
        "cdg.nordest@orvane.example",
        "Thomas Weber",
        "Contrôle de gestion région",
        "Nord-Est",
    ),
    (
        "USER",
        "cdg.sudouest@orvane.example",
        "Inès Darrieux",
        "Contrôle de gestion région",
        "Sud-Ouest",
    ),
    (
        "USER",
        "dir.sud@orvane.example",
        "Paul Marchetti",
        "Direction de zone Sud",
        "Sud-Est",
    ),
    (
        "USER",
        "dir.sud@orvane.example",
        "Paul Marchetti",
        "Direction de zone Sud",
        "Sud-Ouest",
    ),
]

SEUILS = [
    ("Indicateur", "Sens", "Seuil vert", "Seuil orange", "Unité", "Lecture"),
    (
        "Écart CA vs budget",
        "haut",
        0.0,
        -0.02,
        "%",
        "Vert si >= 0 %, orange jusqu'à -2 %, rouge en dessous",
    ),
    (
        "Écart taux de marge brute vs budget",
        "haut",
        0.0,
        -0.01,
        "points",
        "Vert si >= 0 pt, orange jusqu'à -1 pt",
    ),
    (
        "Écart EBITDA vs budget",
        "haut",
        0.0,
        -0.05,
        "%",
        "Vert si >= 0 %, orange jusqu'à -5 %",
    ),
    (
        "Écart DSO vs objectif",
        "bas",
        0.0,
        5.0,
        "jours",
        "Vert si <= objectif, orange jusqu'à +5 jours",
    ),
    (
        "Part des créances échues",
        "bas",
        0.30,
        0.40,
        "%",
        "Vert si <= 30 %, orange jusqu'à 40 %",
    ),
]

if CIBLE.exists():
    sys.exit(f"{CIBLE} existe déjà : modifie-le dans Excel, il n'est pas recréé.")

CIBLE.parent.mkdir(exist_ok=True)
wb = Workbook()
wb.remove(wb.active)
for nom, lignes in (("Général", GENERAL), ("Sécurité", SECURITE), ("Seuils", SEUILS)):
    ws = wb.create_sheet(nom)
    for ligne in lignes:
        ws.append(ligne)
    for cellule in ws[1]:
        cellule.font = Font(bold=True, color="FFFFFF")
        cellule.fill = PatternFill("solid", fgColor="1F3A5F")
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = (
            max(len(str(c.value)) for c in col) + 2
        )
    ws.freeze_panes = "A2"
wb.save(CIBLE)
print(f"Classeur de paramètres créé : {CIBLE}")
