"""Étape 3 : génère les feuilles Qlik Sense à partir des conversions et les envoie par l'API.

Usage :
    python lab02/generer.py                  écrit les feuilles dans sorties/feuilles/
    python lab02/generer.py --creer          crée une application, charge les données, envoie
    python lab02/generer.py <identifiant>    envoie les feuilles dans une application existante

Chaque visuel Spotfire donne un objet Qlik Sense du type correspondant, posé sur une grille
régulière. Les briques d'objets (gabarits JSON, dimension, mesure) sont celles du LAB 01.
L'envoi passe par l'outil en ligne de commande « qlik », qui appelle les API de Qlik Sense Cloud.
Avec --creer, la variable d'environnement QLIK_ADMINISTRATEUR donne l'adresse e-mail de la
personne qui recharge : elle remplace le texte à compléter du script, sans être écrite ici.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

DOSSIER = pathlib.Path(__file__).parent
RACINE = DOSSIER.parent
SORTIES = DOSSIER / "sorties"
sys.path.insert(0, str(RACINE / "qlik"))

import construire_feuilles as briques  # noqa: E402

NOM = "Contrôle de gestion Orvane - LAB 02 (généré)"
A_COMPLETER = "A_REMPLACER_PAR_TON_EMAIL_QLIK"
COLONNES, LIGNES = 24, 24
SERIES = ("Color", "Line")  # axes Spotfire qui découpent en séries


def mesures_de(visuel, *axes):
    return [m for m in visuel["mesures"] if m["axe"] in axes and "qlik" in m]


def poser_mesures(visuel, axes=("Y", "Measure"), **options):
    return [
        briques.mesure(
            m["qlik"], m["libelle"] or visuel["titre"], briques.F_DECIMAL, **options
        )
        for m in mesures_de(visuel, *axes)
    ]


def poser_dimensions(visuel, garder=None):
    choisies = [d for d in visuel["dimensions"] if garder is None or d["axe"] in garder]
    choisies.sort(key=lambda d: d["axe"] in SERIES)  # l'axe d'abord, les séries ensuite
    return [briques.dimension(d["qlik"], d["spotfire"]) for d in choisies]


def objet(visuel):
    """L'objet Qlik Sense d'un visuel converti, ou None s'il n'y a pas de règle pour ce type."""
    sorte, titre = visuel["type"], visuel["titre"]
    if "arbitrage" in visuel or not mesures_de(visuel, "Y", "Measure", "Size"):
        return None
    if sorte == "Kpi":
        valeur = mesures_de(visuel, "Y")[0]
        carte = briques.carte_kpi(
            titre, valeur["libelle"], valeur["qlik"], briques.F_DECIMAL
        )
        cube = carte["qProperty"]["qHyperCubeDef"]
        for seconde in mesures_de(visuel, "Comparative")[:1]:
            carte["qProperty"]["footnote"] = seconde["libelle"]
            cube["qMeasures"].append(
                briques.mesure(seconde["qlik"], seconde["libelle"], briques.F_DECIMAL)
            )
        cube["qInitialDataFetch"][0]["qWidth"] = len(cube["qMeasures"])
        return carte
    if sorte in ("BarChart", "WaterfallChart"):
        return briques.barres(
            titre, "", poser_dimensions(visuel), poser_mesures(visuel)
        )
    if sorte == "LineChart":
        return briques.courbes(
            titre, "", poser_dimensions(visuel), poser_mesures(visuel)
        )
    if sorte == "CombinationChart":
        mesures = poser_mesures(visuel)
        for rang, mesure in enumerate(mesures):
            mesure["qDef"]["series"] = {
                "type": "bar" if rang == 0 else "line",
                "axis": 0,
            }
        return briques.combine(titre, "", poser_dimensions(visuel, ("X",)), mesures)
    if sorte == "CrossTablePlot":
        lignes = poser_dimensions(visuel, ("Row",))
        return briques.croise(
            titre,
            "",
            lignes,
            poser_dimensions(visuel, ("Column",)),
            poser_mesures(visuel),
        )
    if sorte == "Maps.MapChart":
        taille = mesures_de(visuel, "Size")[0]["qlik"]
        teinte = mesures_de(visuel, "Color")
        couleur = "RGB(31,58,95)"
        if teinte:  # la couleur Spotfire suit une mesure : vert au-dessus de zéro, rouge en dessous
            couleur = "If(%s >= 0, RGB(34,139,94), RGB(214,69,65))" % teinte[0]["qlik"]
        return briques.carte(titre, "", [briques.couche_points(taille, couleur, "''")])
    return None


def feuille(rang, page):
    """Une feuille : les cartes d'indicateurs en haut, les autres visuels en grille dessous."""
    objets = [(v, objet(v)) for v in page["visuels"]]
    cartes = [o for v, o in objets if o and v["type"] == "Kpi"]
    autres = [o for v, o in objets if o and v["type"] != "Kpi"]
    enfants, cellules = [], []

    def poser(o, *place):
        enfants.append(o)
        cellules.append(briques.cellule(o, *place))

    par_rangee = 5
    for i, carte in enumerate(cartes):
        carte["qProperty"]["fontSize"] = "S"
        largeur = COLONNES / min(par_rangee, len(cartes))
        poser(carte, (i % par_rangee) * largeur, 3 * (i // par_rangee), largeur, 3)
    haut = 3 * -(-len(cartes) // par_rangee)
    par_ligne = 2 if len(autres) <= 4 else 3
    rangees = -(-len(autres) // par_ligne) or 1
    hauteur = (LIGNES - haut) / rangees
    for i, o in enumerate(autres):
        largeur = COLONNES / par_ligne
        poser(
            o,
            (i % par_ligne) * largeur,
            haut + (i // par_ligne) * hauteur,
            largeur,
            hauteur,
        )
    return {
        "qProperty": {
            "qInfo": {"qId": "lab02-feuille-%d" % (rang + 1), "qType": "sheet"},
            "qMetaDef": {
                "title": page["titre"],
                "description": "Feuille générée par le LAB 02",
            },
            "rank": rang,
            "thumbnail": {"qStaticContentUrlDef": {}},
            "columns": COLONNES,
            "rows": LIGNES,
            "gridResolution": "small",
            "layoutOptions": {"mobileLayout": "LIST", "extendable": False},
            "cells": cellules,
            "qChildListDef": {"qData": {"title": "/title"}},
        },
        "qChildren": enfants,
    }


def qlik(*arguments, attente=300):
    sortie = subprocess.run(
        ["qlik", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=attente,
    )
    if sortie.returncode != 0:
        sys.exit(
            "qlik %s : %s"
            % (arguments[0], (sortie.stderr or sortie.stdout).strip()[:400])
        )
    return sortie.stdout.strip()


def creer_application():
    """Application neuve : script de chargement du dépôt, puis rechargement des données."""
    administrateur = os.environ.get("QLIK_ADMINISTRATEUR", "")
    if "@" not in administrateur:
        sys.exit(
            "Variable QLIK_ADMINISTRATEUR absente : sans elle, l'application se ferme à son auteur."
        )
    application = qlik("app", "create", "--attributes-name", NOM, "-q")
    script = (RACINE / "qlik" / "chargement.qvs").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as provisoire:
        fichier = pathlib.Path(provisoire) / "chargement.qvs"
        fichier.write_text(
            script.replace(A_COMPLETER, administrateur, 1), encoding="utf-8"
        )
        qlik("app", "script", "set", str(fichier), "--app", application)
    rechargement = qlik("reload", "create", "--appId", application, "-q")
    for _ in range(60):
        etat = json.loads(qlik("reload", "get", rechargement, "--json"))["status"]
        if etat in ("SUCCEEDED", "FAILED", "CANCELED", "EXCEEDED_LIMIT"):
            break
        time.sleep(5)
    if etat != "SUCCEEDED":
        sys.exit("Rechargement de %s : %s" % (application, etat))
    return application


def main():
    pages = json.loads((SORTIES / "conversions.json").read_text(encoding="utf-8"))
    dossier = SORTIES / "feuilles"
    dossier.mkdir(exist_ok=True)
    generes = attendus = 0
    for rang, page in enumerate(pages):
        contenu = feuille(rang, page)
        (dossier / ("feuille_%d.json" % (rang + 1))).write_text(
            json.dumps(contenu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        generes += len(contenu["qChildren"])
        attendus += len(page["visuels"])
        print(
            "%-36s %d objets sur %d visuels"
            % (page["titre"], len(contenu["qChildren"]), len(page["visuels"]))
        )
    print("%d objets générés sur %d visuels" % (generes, attendus))
    if len(sys.argv) == 2:
        application = creer_application() if sys.argv[1] == "--creer" else sys.argv[1]
        qlik("app", "object", "set", str(dossier / "*.json"), "--app", application)
        print("Feuilles envoyées dans l'application %s" % application)


if __name__ == "__main__":
    main()
