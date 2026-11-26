"""Écrit data.js, les chiffres affichés par la page du dépôt (index.html).

Tout vient des fichiers du dépôt : data/ pour les montants et les profils de sécurité,
lab02/sorties/ pour les comptes de la migration par scripts. Rien n'est saisi à la main.
Usage : python docs/site/generer_data.py
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
EXERCICE, DERNIER_MOIS_CLOS = 2026, 10


def lire(nom):
    with open(RACINE / "data" / nom, encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


def cumul(ligne):
    return (
        int(float(ligne["Exercice"])) == EXERCICE
        and int(float(ligne["Mois"])) <= DERNIER_MOIS_CLOS
    )


ca = defaultdict(float)
for ligne in lire("ventes.csv"):
    if cumul(ligne):
        ca[ligne["Région"]] += float(ligne["CA Réel"])

agences = defaultdict(set)
for ligne in lire("ventes_agences.csv"):
    agences[ligne["Région"]].add(ligne["Agence"])

regions = sorted(ca)
profils = {}
for ligne in lire("securite.csv"):
    if ligne["ACCESS"] != "USER":
        continue
    profil = profils.setdefault(
        ligne["Nom"], {"nom": ligne["Nom"], "profil": ligne["Profil"], "regions": []}
    )
    profil["regions"] += regions if ligne["Région"] == "*" else [ligne["Région"]]
for profil in profils.values():
    profil["groupe"] = len(profil["regions"]) == len(regions)
    profil["ca"] = round(sum(ca[r] for r in profil["regions"]), 2)
    profil["agences"] = sum(len(agences[r]) for r in profil["regions"])

pages = json.loads(
    (RACINE / "lab02/sorties/inventaire.json").read_text(encoding="utf-8")
)["pages"]
conversions = json.loads(
    (RACINE / "lab02/sorties/conversions.json").read_text(encoding="utf-8")
)
controle = (RACINE / "lab02/sorties/controle.md").read_text(encoding="utf-8")
lignes = [
    re.split(r"\s*\|\s*", ligne.strip("| "))
    for ligne in controle.splitlines()
    if ligne.startswith("| ")
][1:]

donnees = {
    "regions": [
        {"nom": r, "ca": round(ca[r], 2), "agences": len(agences[r])} for r in regions
    ],
    "caTotal": round(sum(ca.values()), 2),
    "agencesTotal": sum(len(a) for a in agences.values()),
    "profils": list(profils.values()),
    "lab02": {
        "pages": len(pages),
        "visuels": sum(len(page["visuels"]) for page in pages),
        "formules": sum(
            len(v["mesures"]) for page in conversions for v in page["visuels"]
        ),
        "visuelsControles": len(lignes),
        "points": sum(int(ligne[3]) for ligne in lignes),
        "conformes": sum(int(ligne[4]) for ligne in lignes),
    },
}
(RACINE / "data.js").write_text(
    "// Généré par docs/site/generer_data.py : ne pas modifier à la main.\n"
    "window.ORVANE = " + json.dumps(donnees, ensure_ascii=False, indent=1) + ";\n",
    encoding="utf-8",
)
print("data.js écrit :", donnees["caTotal"], donnees["agencesTotal"], donnees["lab02"])
