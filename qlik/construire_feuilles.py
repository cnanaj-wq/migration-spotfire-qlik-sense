"""Génère les cinq feuilles de l'application Qlik Sense « Contrôle de gestion Orvane ».

Chaque feuille est écrite dans qlik/feuilles/ sous forme d'un fichier JSON, puis envoyée
dans l'application avec la ligne de commande Qlik Sense :

    python qlik/construire_feuilles.py
    qlik app object set "qlik/feuilles/*.json" --app <identifiant de l'application>

Toutes les feuilles ont la même ossature : la navigation en haut, les mêmes filtres
repliés juste en dessous, une rangée de cartes d'indicateurs, puis les graphiques.
"""

import copy
import io
import json
import os
import re
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
GABARITS = os.path.join(ICI, "gabarits")
SORTIE = os.path.join(ICI, "feuilles")

# Charte Orvane, la même que dans Spotfire
BLEU_NUIT = "#1F3A5F"
GRIS = "#A7B1BD"
AMBRE = "#E0A458"
VERT = "#228B5E"
ROUGE = "#D64541"
SARCELLE = "#2A9D8F"
SABLE = "#E9C46A"
CORAIL = "#E76F51"
FOND_SOLDE = "#D6E2F0"

COLONNES, LIGNES = 24, 24

# ---------------------------------------------------------------- expressions
# L'exercice suit la sélection : sans sélection, c'est le dernier exercice chargé.
EXERCICE = "Exercice={$(=Max(Exercice))}"
EXERCICE_N1 = "Exercice={$(=Max(Exercice)-1)}"
DERNIER_MOIS = "Mois={$(=Max({<[Mois clos]={1}>} Mois))}"
CUMUL = "{<%s, [Mois clos]={1}%%s>}" % EXERCICE  # cumul sur les mois clôturés
ANNEE = "{<%s>}" % EXERCICE  # les douze mois de l'exercice
FIN = "{<%s, %s>}" % (EXERCICE, DERNIER_MOIS)  # dernier mois clôturé
FIN_N1 = "{<%s, %s>}" % (EXERCICE_N1, DERNIER_MOIS)


def somme(champ, filtre=""):
    """Cumul de l'exercice sur les mois clôturés."""
    return "Sum(%s [%s])" % (CUMUL % (", " + filtre if filtre else ""), champ)


def ecart_pct(reel, reference):
    return "(%s) / (%s) - 1" % (reel, reference)


def rvb(couleur):
    """Couleur hexadécimale écrite pour une expression Qlik."""
    return "RGB(%d, %d, %d)" % tuple(int(couleur[i : i + 2], 16) for i in (1, 3, 5))


def couleur_signe(expression, hausse_favorable=True):
    bon, mauvais = (VERT, ROUGE) if hausse_favorable else (ROUGE, VERT)
    return "If((%s) >= 0, '%s', '%s')" % (expression, bon, mauvais)


CA, CA_B, CA_N1 = somme("CA Réel"), somme("CA Budget"), somme("CA N-1")
MB, MB_B, MB_N1 = (
    somme("Marge brute Réel"),
    somme("Marge brute Budget"),
    somme("Marge brute N-1"),
)
TAUX, TAUX_B, TAUX_N1 = (
    "(%s) / (%s)" % (MB, CA),
    "(%s) / (%s)" % (MB_B, CA_B),
    "(%s) / (%s)" % (MB_N1, CA_N1),
)


def solde(colonne, rang, comparaison="<="):
    """Solde du compte de résultat : somme des rubriques jusqu'au rang donné."""
    filtre = '[Ordre rubrique]={"%s%d"}' % (comparaison, rang)
    if comparaison == "=":
        filtre = "[Ordre rubrique]={%d}" % rang
    return somme("CR " + colonne, filtre)


AG_CA, AG_CA_B = somme("Agence CA Réel"), somme("Agence CA Budget")
AG_MB = somme("Agence Marge brute Réel")

# ---------------------------------------------------------------- formats
F_ENTIER = ("# ##0", 0)
F_KE = ("# ##0 k€", 0)
F_ME = ("# ##0,0 M€", 1)
F_PCT = ("0,0 %", 1)
F_ECART = ("+0,0 %;-0,0 %", 1)
F_POINTS = ("+0,0 pts;-0,0 pts", 1)
F_JOURS = ("0,0 j", 1)
F_DECIMAL = ("# ##0,0", 1)


def format_nombre(modele):
    motif, decimales = modele
    return {
        "qType": "F",
        "qnDec": decimales,
        "qUseThou": 1,
        "qFmt": motif,
        "qDec": ",",
        "qThou": " ",
    }


# ---------------------------------------------------------------- briques
def gabarit(nom):
    chemin = os.path.join(GABARITS, nom + ".json")
    return json.load(io.open(chemin, encoding="utf-8"))


def identifiant():
    return uuid.uuid4().hex[:12]


_DIM = gabarit("barchart")["qProperty"]["qHyperCubeDef"]["qDimensions"][0]
_MES = gabarit("sn-table")["qProperty"]["qHyperCubeDef"]["qMeasures"][0]


def dimension(champ, libelle, tri="auto", sans_vide=False, limite=None):
    d = copy.deepcopy(_DIM)
    d["qDef"]["qFieldDefs"] = [champ]
    d["qDef"]["qFieldLabels"] = [libelle]
    d["qDef"]["cId"] = identifiant()
    if tri == "numerique":
        d["qDef"]["autoSort"] = False
        d["qDef"]["qSortCriterias"] = [{"qSortByNumeric": 1, "qExpression": {}}]
    if sans_vide:
        d["qNullSuppression"] = True
    if limite:
        d["qOtherTotalSpec"] = {
            "qOtherMode": "OTHER_COUNTED",
            "qOtherCounted": {"qv": str(limite)},
            "qOtherLimit": {},
            "qOtherLimitMode": "OTHER_GE_LIMIT",
            "qSuppressOther": True,
            "qForceBadValueKeeping": True,
            "qApplyEvenWhenPossiblyWrongResult": True,
            "qOtherSortMode": "OTHER_SORT_DESCENDING",
            "qTotalMode": "TOTAL_OFF",
            "qReferencedExpression": {},
        }
    return d


def mesure(expression, libelle, modele=F_ENTIER, couleur=None, fond=None, **options):
    m = copy.deepcopy(_MES)
    m["qDef"]["qDef"] = expression
    m["qDef"]["qLabel"] = libelle
    m["qDef"]["cId"] = identifiant()
    m["qDef"]["qNumFormat"] = format_nombre(modele)
    m["qDef"]["isCustomFormatted"] = True
    m["qDef"]["numFormatFromTemplate"] = False
    m["qDef"].update(options)
    if couleur:
        m["qAttributeExpressions"].append(
            {"qExpression": couleur, "id": "colorByExpression"}
        )
    if fond:
        m["qAttributeExpressions"].append(
            {"qExpression": fond, "id": "cellBackgroundColor"}
        )
    return m


def style_carte(fond="#FFFFFF", bord="#DCE3EA"):
    """Habillage commun : carte blanche aux angles arrondis, titres aux couleurs de la charte."""
    return {
        "key": "general",
        "title": {
            "main": {"fontSize": "16px", "color": {"index": -1, "color": BLEU_NUIT}},
            "subTitle": {
                "fontSize": "12px",
                "color": {"index": -1, "color": "#617386"},
            },
            "footer": {"fontSize": "12px", "color": {"index": -1, "color": "#617386"}},
        },
        "borderRadius": "12px",
        "borderWidth": "1px",
        "borderColor": {"color": bord, "index": -1},
        "bgColor": {"useColor": True, "color": {"color": fond, "index": -1}},
    }


def objet(nom_gabarit, titre, sous_titre=""):
    o = gabarit(nom_gabarit)
    p = o["qProperty"]
    p["qInfo"]["qId"] = identifiant()
    p["title"] = titre
    p["subtitle"] = sous_titre
    p["footnote"] = ""
    p.pop("hash", None)
    p["components"] = [c for c in p.get("components", []) if c.get("key") != "general"]
    p["components"].append(style_carte())
    o["qChildren"] = []
    return o


def cube(o, dimensions, mesures, tri_mesure=None):
    """Pose dimensions et mesures ; tri_mesure = rang de la mesure qui trie, décroissant."""
    h = o["qProperty"]["qHyperCubeDef"]
    h["qDimensions"] = dimensions
    h["qMeasures"] = mesures
    ordre = list(range(len(dimensions) + len(mesures)))
    if tri_mesure is not None:
        rang = len(dimensions) + tri_mesure
        ordre = [rang] + [i for i in ordre if i != rang]
        for d in dimensions:
            d["qDef"]["autoSort"] = False
        mesures[tri_mesure]["qSortBy"] = {"qSortByNumeric": -1, "qExpression": {}}
        mesures[tri_mesure]["qDef"]["autoSort"] = False
    h["qInterColumnSortOrder"] = ordre
    h["qInitialDataFetch"][0]["qWidth"] = max(len(ordre), 2)
    return o


def colorer_par_expression(o, expression):
    o["qProperty"]["color"].update(
        {
            "auto": False,
            "mode": "byExpression",
            "colorExpression": expression,
            "expressionIsColor": True,
        }
    )
    for m in o["qProperty"]["qHyperCubeDef"]["qMeasures"]:
        m["qAttributeExpressions"].append(
            {"qExpression": expression, "id": "colorByExpression"}
        )


BIBLIOTHEQUE = []

COULEURS_BU = [
    ("Chauffage & Climatisation", BLEU_NUIT),
    ("Électricité", AMBRE),
    ("Outillage", SARCELLE),
    ("Services", CORAIL),
]


def series_par_bu(o, expression, modele):
    """Une série par BU, à sa couleur. Le signe *= garde la sélection de BU en cours."""
    o["qProperty"]["qHyperCubeDef"]["qMeasures"] = [
        mesure(expression.replace("{<", "{<BU*={'%s'}, " % bu), bu, modele)
        for bu, _ in COULEURS_BU
    ]
    couleurs_mesures(o, [couleur for _, couleur in COULEURS_BU])


def couleurs_mesures(o, couleurs):
    """Une couleur fixe par série : chaque série devient une mesure de bibliothèque colorée."""
    p = o["qProperty"]
    for m, couleur in zip(p["qHyperCubeDef"]["qMeasures"], couleurs):
        definition = m["qDef"]
        libelle = definition.pop("qLabel")
        cle = "orv-" + re.sub(
            "[^a-z0-9]+", "-", (p["title"] + " " + libelle).lower()
        ).strip("-")
        BIBLIOTHEQUE.append(
            {
                "qInfo": {"qId": cle, "qType": "measure"},
                "qMeasure": {
                    "qLabel": "%s - %s" % (p["title"], libelle),
                    "qDef": definition.pop("qDef"),
                    "qGrouping": "N",
                    "qExpressions": [],
                    "qActiveExpression": 0,
                    "qLabelExpression": "'%s'" % libelle.replace("'", "''"),
                    "coloring": {"baseColor": {"color": couleur, "index": -1}},
                    "qNumFormat": definition["qNumFormat"],
                    "isCustomFormatted": True,
                },
                "qMetaDef": {
                    "title": "%s - %s" % (p["title"], libelle),
                    "description": p["subtitle"],
                    "tags": [],
                },
            }
        )
        m["qLibraryId"] = cle
        definition["qLabelExpression"] = "'%s'" % libelle.replace("'", "''")
    p["color"].update({"auto": True, "useBaseColors": "measure"})


def barres(
    titre, sous_titre, dimensions, mesures, horizontal=False, tri=None, **reglages
):
    o = cube(objet("barchart", titre, sous_titre), dimensions, mesures, tri)
    p = o["qProperty"]
    p["orientation"] = "horizontal" if horizontal else "vertical"
    p["dataPoint"]["showLabels"] = reglages.get("etiquettes", True)
    p["barGrouping"]["grouping"] = reglages.get("groupement", "grouped")
    p["scrollbar"] = "bar"
    p["legend"]["showTitle"] = False
    p["dimensionAxis"]["show"] = "labels"
    p["measureAxis"]["show"] = "labels"
    return o


def courbes(titre, sous_titre, dimensions, mesures):
    o = cube(objet("linechart", titre, sous_titre), dimensions, mesures)
    p = o["qProperty"]
    p["scrollbar"] = "none"
    p["preferContinuousAxis"] = False
    p["dataPoint"]["show"] = True
    p["legend"]["showTitle"] = False
    p["dimensionAxis"]["show"] = "labels"
    p["measureAxis"]["show"] = "labels"
    p["qHyperCubeDef"]["qSuppressZero"] = True
    return o


def combine(titre, sous_titre, dimensions, mesures):
    o = cube(objet("combochart", titre, sous_titre), dimensions, mesures)
    p = o["qProperty"]
    p["scrollbar"] = "none"
    p["legend"]["showTitle"] = False
    p["dimensionAxis"]["show"] = "labels"
    for axe in p["measureAxes"]:
        axe["show"] = "labels"
    return o


def tableau(titre, sous_titre, dimensions, mesures, tri=None, totaux=True):
    o = cube(objet("sn-table", titre, sous_titre), dimensions, mesures, tri)
    p = o["qProperty"]
    p["qHyperCubeDef"]["qColumnOrder"] = list(range(len(dimensions) + len(mesures)))
    p["totals"] = {
        "show": False,
        "position": "top" if totaux else "noTotals",
        "label": "Total",
    }
    p["usePagination"] = False
    return o


def croise(titre, sous_titre, lignes, colonnes, mesures):
    o = cube(objet("sn-pivot-table", titre, sous_titre), lignes + colonnes, mesures)
    h = o["qProperty"]["qHyperCubeDef"]
    h["qNoOfLeftDims"] = len(lignes)
    h["qShowTotalsAbove"] = False
    h.pop("rankedList", None)
    return o


def cascade(titre, sous_titre, barres_cascade, total):
    """Graphique en cascade : une mesure par barre, puis un sous-total final."""
    mesures = []
    for rang, (libelle, expression) in enumerate(barres_cascade):
        dernier = rang == len(barres_cascade) - 1
        mesures.append(
            mesure(
                expression,
                libelle,
                F_ENTIER,
                valueType="NORMAL",
                subtotal={"enable": dernier, "label": total},
            )
        )
    o = {
        "qProperty": {
            "qInfo": {"qId": identifiant(), "qType": "waterfallchart"},
            "qMetaDef": {},
            "visualization": "waterfallchart",
            "showTitles": True,
            "title": titre,
            "subtitle": sous_titre,
            "footnote": "",
            # attendu par le graphique en cascade, qui formate lui-même ses étiquettes
            "qDef": {"isCustomFormatted": False},
            "components": [style_carte()],
            "qHyperCubeDef": {
                "qDimensions": [],
                "qMeasures": mesures,
                "qInterColumnSortOrder": [],
                "qInitialDataFetch": [
                    {"qLeft": 0, "qTop": 0, "qWidth": len(mesures), "qHeight": 1}
                ],
                "qMode": "S",
                "qSuppressMissing": True,
            },
            "color": {
                "auto": False,
                "positiveValue": {"paletteColor": {"index": -1, "color": VERT}},
                "negativeValue": {"paletteColor": {"index": -1, "color": ROUGE}},
                "subtotal": {"paletteColor": {"index": -1, "color": BLEU_NUIT}},
            },
            "dataPoint": {"showLabels": True},
            "dimensionAxis": {"show": "labels", "label": "auto", "dock": "near"},
            "measureAxis": {
                "show": "labels",
                "dock": "near",
                "spacing": 1,
                "autoMinMax": True,
                "minMax": "min",
                "min": 0,
                "max": 10,
            },
            "gridLine": {"auto": True, "spacing": 2},
            "legend": {"show": False, "dock": "auto"},
        },
        "qChildren": [],
    }
    return o


def carte_kpi(titre, sous_titre, valeur, modele, reference=None, pied=None, **reglages):
    """Carte d'indicateur : la valeur en grand, l'écart coloré en dessous.

    reference = (expression, libellé, format, hausse favorable ?)
    """
    o = objet("kpi", titre, sous_titre)
    p = o["qProperty"]
    p["showMeasureTitle"] = False
    p["textAlign"] = "left"
    p["fontSize"] = reglages.get("taille", "M")
    p["layoutBehavior"] = "fixed"
    principale = mesure(valeur, titre, modele)
    principale["qDef"]["conditionalColoring"] = {
        "useConditionalColoring": False,
        "singleColor": 3,
        "paletteSingleColor": {"index": -1, "color": BLEU_NUIT},
        "segments": {
            "limits": [],
            "paletteColors": [{"index": -1, "color": BLEU_NUIT}],
        },
    }
    mesures = [principale]
    if reference:
        expression, libelle, modele_ref, hausse = reference
        bas, haut = (ROUGE, VERT) if hausse else (VERT, ROUGE)
        seconde = mesure(expression, libelle, modele_ref)
        seconde["qDef"]["conditionalColoring"] = {
            "useConditionalColoring": True,
            "singleColor": 3,
            "paletteSingleColor": {"index": -1, "color": BLEU_NUIT},
            "segments": {
                "limits": [{"value": 0, "gradient": False, "normal": 0}],
                "paletteColors": [
                    {"index": -1, "color": bas},
                    {"index": -1, "color": haut},
                ],
            },
        }
        mesures.append(seconde)
        # fond de la carte selon l'écart, comme les tuiles Spotfire : vert, ambre, rouge
        favorable = "(%s)" % expression if hausse else "-(%s)" % expression
        # tolérance avant le rouge : 5 % d'écart, 1 point de taux ou 3 jours de délai
        seuil = 0.05
        if "pts" in modele_ref[0]:
            seuil = 1
        elif " j" in modele_ref[0]:
            seuil = 3
        general = [c for c in p["components"] if c.get("key") == "general"][0]

        # une propriété peut être une expression : la couleur suit alors la sélection
        def selon_ecart(bon, moyen, mauvais):
            return {
                "qStringExpression": {
                    "qExpr": "If(%s >= 0, '%s', If(%s >= -%s, '%s', '%s'))"
                    % (favorable, bon, favorable, seuil, moyen, mauvais)
                }
            }

        general["bgColor"] = {
            "useColor": True,
            "color": {
                "index": -1,
                "color": selon_ecart("#E3F3EA", "#FBF0DD", "#FADFDD"),
            },
        }
        general["borderColor"] = {"index": -1, "color": selon_ecart(VERT, AMBRE, ROUGE)}
        general["borderWidth"] = "2px"
    if pied:
        p["footnote"] = {"qStringExpression": {"qExpr": pied}}
    p["qHyperCubeDef"]["qMeasures"] = mesures
    p["qHyperCubeDef"]["qInitialDataFetch"][0]["qWidth"] = len(mesures)
    return o


def pied_n1(reel, n1, modele=F_ECART, points=False):
    ecart = "(%s) - (%s)" % (reel, n1) if points else ecart_pct(reel, n1)
    if points:
        return "'vs N-1 : ' & Num(100 * (%s), '+0,0;-0,0') & ' pts'" % ecart
    return "'vs N-1 : ' & Num(%s, '%s')" % (ecart, modele[0])


# ---------------------------------------------------------------- ossature commune
FEUILLES = [
    ("orv-synthese", "Synthèse direction"),
    ("orv-ca-marge", "Chiffre d'affaires et marge"),
    ("orv-agences", "Carte des agences"),
    ("orv-ecarts", "Écarts et compte de résultat"),
    ("orv-bfr", "BFR, trésorerie et balance âgée"),
]
FILTRES = [
    ("Exercice", "Exercice"),
    ("Mois nom", "Mois"),
    ("BU", "BU"),
    ("Région", "Région"),
    ("Canal", "Canal"),
]


def bouton(cible, libelle, actif):
    o = gabarit("action-button")
    p = o["qProperty"]
    p["qInfo"]["qId"] = identifiant()
    p["navigation"] = {"action": "goToSheet", "sheet": cible}
    p["style"]["label"] = libelle
    p["style"]["font"]["color"] = {
        "index": -1,
        "color": BLEU_NUIT if actif else "#ffffff",
    }
    p["style"]["font"]["sizeFixed"] = 13
    p["style"]["background"]["color"] = {
        "index": -1,
        "color": AMBRE if actif else BLEU_NUIT,
    }
    p["style"]["border"] = {"radius": 0.25, "useBorder": False}
    o["qChildren"] = []
    return o


def panneau_filtres():
    """Les mêmes filtres sur toutes les feuilles, repliés : on les déplie d'un clic."""
    panneau = gabarit("filterpane")
    panneau["qProperty"]["qInfo"]["qId"] = identifiant()
    panneau["qProperty"]["showTitles"] = False
    panneau["qChildren"] = []
    for champ, libelle in FILTRES:
        liste = gabarit("listbox")
        p = liste["qProperty"]
        p["qInfo"]["qId"] = identifiant()
        c = "[%s]" % champ
        p["title"] = {
            "qStringExpression": {
                "qExpr": "'%s' & Chr(10) & If(GetSelectedCount(%s)=0, 'Tout', "
                "If(GetSelectedCount(%s)<=2, GetFieldSelections(%s,', '), "
                "GetSelectedCount(%s) & ' sélectionnés'))" % (libelle, c, c, c, c)
            }
        }
        definition = p["qListObjectDef"]["qDef"]
        definition["qFieldDefs"] = [champ]
        definition["qFieldLabels"] = [libelle]
        definition["qSortCriterias"] = [
            {
                "qSortByState": 1,
                "qSortByNumeric": 1,
                "qSortByAscii": 1,
                "qExpression": {},
            }
        ]
        liste["qChildren"] = []
        panneau["qChildren"].append(liste)
    return panneau


def cellule(o, colonne, ligne, largeur, hauteur):
    p = o["qProperty"]
    return {
        "name": p["qInfo"]["qId"],
        "type": p.get("visualization") or p["qInfo"]["qType"],
        "col": colonne,
        "row": ligne,
        "colspan": largeur,
        "rowspan": hauteur,
        "bounds": {
            "x": 100.0 * colonne / COLONNES,
            "y": 100.0 * ligne / LIGNES,
            "width": 100.0 * largeur / COLONNES,
            "height": 100.0 * hauteur / LIGNES,
        },
    }


def feuille(rang, description, cartes, graphiques):
    """cartes : rangée d'indicateurs ; graphiques : (objet, colonne, ligne, largeur, hauteur)."""
    cle, titre = FEUILLES[rang]
    enfants, cellules = [], []

    def poser(o, *place):
        enfants.append(o)
        cellules.append(cellule(o, *place))

    largeur = COLONNES / float(len(FEUILLES))
    for i, (cible, libelle) in enumerate(FEUILLES):
        poser(bouton(cible, libelle, i == rang), i * largeur, 0, largeur, 1.5)
    poser(panneau_filtres(), 0, 1.5, COLONNES, 2)
    largeur = COLONNES / float(len(cartes))
    for i, carte in enumerate(cartes):
        # au-delà de quatre cartes, ou avec un pied de carte, la valeur passe en petit
        if len(cartes) > 4 or any(c["qProperty"].get("footnote") for c in cartes):
            carte["qProperty"]["fontSize"] = "S"
        poser(carte, i * largeur, 3.5, largeur, 5)
    for o, colonne, ligne, large, haut in graphiques:
        poser(o, colonne, ligne, large, haut)

    return {
        "qProperty": {
            "qInfo": {"qId": cle, "qType": "sheet"},
            "qMetaDef": {"title": titre, "description": description},
            "rank": rang,
            "thumbnail": {"qStaticContentUrlDef": {}},
            "columns": COLONNES,
            "rows": LIGNES,
            "gridResolution": "small",
            "layoutOptions": {"mobileLayout": "LIST", "extendable": False},
            "components": [
                {
                    "key": "general",
                    "bgColor": {
                        "useExpression": False,
                        "color": {"index": -1, "color": "#ffffff"},
                    },
                }
            ],
            "cells": cellules,
            "qChildListDef": {"qData": {"title": "/title"}},
        },
        "qChildren": enfants,
    }


MOIS = lambda: dimension("Mois nom", "Mois", tri="numerique")  # noqa: E731
PERIODE = "cumul de l'exercice sur les mois clôturés"


# ---------------------------------------------------------------- 1. Synthèse direction
def synthese():
    ebitda, ebitda_b, ebitda_n1 = solde("Réel", 7), solde("Budget", 7), solde("N-1", 7)
    bfr = "Sum(%s BFR)" % FIN
    bfr_obj = "Sum(%s [BFR Objectif])" % FIN
    bfr_n1 = "Sum(%s BFR)" % FIN_N1
    cartes = [
        carte_kpi(
            "Chiffre d'affaires",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % CA,
            F_ME,
            (ecart_pct(CA, CA_B), "vs budget", F_ECART, True),
            pied_n1(CA, CA_N1),
        ),
        carte_kpi(
            "Marge brute",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % MB,
            F_ME,
            (ecart_pct(MB, MB_B), "vs budget", F_ECART, True),
            pied_n1(MB, MB_N1),
        ),
        carte_kpi(
            "Taux de marge",
            "Marge brute rapportée au chiffre d'affaires",
            TAUX,
            F_PCT,
            ("100 * ((%s) - (%s))" % (TAUX, TAUX_B), "vs budget", F_POINTS, True),
            pied_n1(TAUX, TAUX_N1, points=True),
        ),
        carte_kpi(
            "EBITDA",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % ebitda,
            F_ME,
            (ecart_pct(ebitda, ebitda_b), "vs budget", F_ECART, True),
            pied_n1(ebitda, ebitda_n1),
        ),
        carte_kpi(
            "BFR",
            "À la fin du dernier mois clôturé",
            "(%s) / 1000000" % bfr,
            F_ME,
            (ecart_pct(bfr, bfr_obj), "vs objectif", F_ECART, False),
            pied_n1(bfr, bfr_n1),
        ),
    ]

    mensuel = courbes(
        "Chiffre d'affaires mensuel",
        "Réel, budget et exercice précédent, en k€",
        [MOIS()],
        [
            mesure(
                "If(Max([Mois clos]) = 1, Sum(%s [CA Réel]) / 1000)" % ANNEE, "Réel"
            ),
            mesure("Sum(%s [CA Budget]) / 1000" % ANNEE, "Budget"),
            mesure("Sum(%s [CA N-1]) / 1000" % ANNEE, "N-1"),
        ],
    )
    couleurs_mesures(mensuel, [BLEU_NUIT, AMBRE, GRIS])

    ecart_marge = "((%s) - (%s)) / 1000" % (MB, MB_B)
    par_bu = barres(
        "Écart de marge brute par BU",
        "Réel moins budget, en k€",
        [dimension("BU", "BU", sans_vide=True)],
        [mesure(ecart_marge, "Écart de marge")],
        tri=0,
    )
    colorer_par_expression(par_bu, couleur_signe(ecart_marge))

    ebitda_mensuel = combine(
        "EBITDA mensuel",
        "Réel en barres, budget en ligne, en k€",
        [MOIS()],
        [
            mesure("(%s) / 1000" % ebitda, "Réel", series={"type": "bar", "axis": 0}),
            mesure(
                "(%s) / 1000" % ebitda_b, "Budget", series={"type": "line", "axis": 0}
            ),
        ],
    )
    couleurs_mesures(ebitda_mensuel, [BLEU_NUIT, AMBRE])

    return feuille(
        0,
        "Réel, écart au budget et à l'exercice précédent.",
        cartes,
        [
            (mensuel, 0, 8.5, 10, 15.5),
            (par_bu, 10, 8.5, 6, 15.5),
            (ebitda_mensuel, 16, 8.5, 8, 15.5),
        ],
    )


# ---------------------------------------------------------------- 2. CA et marge
def ca_marge():
    cartes = [
        carte_kpi(
            "Chiffre d'affaires",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % CA,
            F_ME,
            (ecart_pct(CA, CA_B), "vs budget", F_ECART, True),
            pied_n1(CA, CA_N1),
        ),
        carte_kpi(
            "Écart de chiffre d'affaires",
            "Réel moins budget",
            "((%s) - (%s)) / 1000" % (CA, CA_B),
            ("+# ##0 k€;-# ##0 k€", 0),
            (ecart_pct(CA, CA_B), "du budget", F_ECART, True),
        ),
        carte_kpi(
            "Marge brute",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % MB,
            F_ME,
            (ecart_pct(MB, MB_B), "vs budget", F_ECART, True),
            pied_n1(MB, MB_N1),
        ),
        carte_kpi(
            "Taux de marge",
            "Marge brute rapportée au chiffre d'affaires",
            TAUX,
            F_PCT,
            ("100 * ((%s) - (%s))" % (TAUX, TAUX_B), "vs budget", F_POINTS, True),
            pied_n1(TAUX, TAUX_N1, points=True),
        ),
    ]

    produits = barres(
        "Chiffre d'affaires par produit",
        "Réel contre budget, en k€",
        [dimension("Produit", "Produit", sans_vide=True)],
        [
            mesure("(%s) / 1000" % CA, "Réel"),
            mesure("(%s) / 1000" % CA_B, "Budget"),
        ],
        horizontal=True,
        tri=0,
        etiquettes=False,
    )
    couleurs_mesures(produits, [BLEU_NUIT, AMBRE])

    ecart_ca = ecart_pct(CA, CA_B)
    canaux = barres(
        "Écart de chiffre d'affaires par canal",
        "Réel contre budget, en %",
        [dimension("Canal", "Canal", sans_vide=True)],
        [mesure(ecart_ca, "Écart au budget", F_ECART)],
        tri=0,
    )
    colorer_par_expression(canaux, couleur_signe(ecart_ca))

    taux_bu = courbes(
        "Taux de marge brute mensuel par BU",
        "Marge brute rapportée au chiffre d'affaires",
        [MOIS()],
        [mesure(TAUX, "Taux de marge", F_PCT)],
    )
    series_par_bu(taux_bu, TAUX, F_PCT)

    fond = "ColorMix2(RangeMax(-1, RangeMin(1, (%s) / 0.15)), %s, %s, %s)" % (
        ecart_ca,
        rvb("#E58D8A"),
        rvb("#7CC3A2"),
        rvb("#FFFFFF"),
    )
    regions = croise(
        "Écart de chiffre d'affaires par région et canal",
        "Réel contre budget, en % : rouge sous le budget, vert au-dessus",
        [dimension("Région", "Région", sans_vide=True)],
        [dimension("Canal", "Canal", sans_vide=True)],
        [mesure(ecart_ca, "Écart au budget", F_ECART, fond=fond)],
    )

    indicateurs = tableau(
        "Indicateurs clés par BU",
        "Montants en k€, " + PERIODE,
        [dimension("BU", "BU", sans_vide=True)],
        [
            mesure("(%s) / 1000" % CA, "CA réel"),
            mesure("(%s) / 1000" % CA_B, "CA budget"),
            mesure(ecart_ca, "% vs budget", F_ECART),
            mesure("(%s) / 1000" % CA_N1, "CA N-1"),
            mesure(ecart_pct(CA, CA_N1), "% vs N-1", F_ECART),
            mesure("(%s) / 1000" % MB, "Marge réelle"),
            mesure(TAUX, "Taux réel", F_PCT),
            mesure(TAUX_B, "Taux budget", F_PCT),
            mesure("((%s) - (%s)) / 1000" % (MB, MB_B), "Écart de marge"),
        ],
        tri=0,
    )

    return feuille(
        1,
        "Chiffre d'affaires par produit, écart par canal, indicateurs par BU.",
        cartes,
        [
            (produits, 0, 8.5, 7, 15.5),
            (canaux, 7, 8.5, 6, 7.5),
            (regions, 13, 8.5, 11, 7.5),
            (indicateurs, 7, 16, 10, 8),
            (taux_bu, 17, 16, 7, 8),
        ],
    )


# ---------------------------------------------------------------- 3. Carte des agences
def couche_points(taille, couleur, infobulle, etiquettes=True):
    couche = gabarit("map")["qProperty"]["gaLayers"][0]
    couche["id"] = couche["cId"] = identifiant()
    emplacement = {
        "key": "[Point agence]",
        "label": "Point agence",
        "type": "expression",
    }
    couche["locationOrLatitude"] = emplacement
    couche["locationDefault"] = "[Point agence]"
    couche["color"].update(
        {
            "mode": "byExpression",
            "auto": False,
            "colorExpression": couleur,
            "expressionIsColor": True,
            "opacity": 0.85,
            "outlineOpacity": 1,
            "outline": {"index": -1, "color": "#ffffff"},
        }
    )
    couche["size"].update(
        {
            "expression": {
                "key": taille,
                "label": "Chiffre d'affaires",
                "type": "expression",
                "qNumFormat": {"qType": "U"},
            },
            "slider": [5, 20],
            "radiusMin": 5,
            "radiusMax": 20,
            "autoRadiusValueRange": True,
            "shape": "points",
        }
    )
    couche["label"]["show"] = etiquettes
    couche["label"]["expression"] = {
        "key": "Agence",
        "label": "Agence",
        "type": "expression",
    }
    couche["tooltip"] = {
        "auto": True,
        "title": {"qStringExpression": {"qExpr": "Agence"}},
        "description": {"qStringExpression": {"qExpr": infobulle}},
        "hideBasic": True,
    }
    d = dimension("Agence", "Agence", sans_vide=True)
    d["qAttributeExpressions"] = [
        {"qExpression": "[Point agence]", "id": "locationOrLatitude"},
        {"qExpression": taille, "id": "size"},
        {"qExpression": couleur, "id": "colorByExpression"},
        {"qExpression": "Agence", "id": "label"},
        {"qExpression": "Agence", "id": "customTooltipTitle"},
        {"qExpression": infobulle, "id": "customTooltipDescription"},
    ]
    couche["qHyperCubeDef"]["qDimensions"] = [d]
    couche["qHyperCubeDef"]["qInitialDataFetch"][0]["qHeight"] = 1000
    return couche


def couche_secteurs(valeur, libelle, decoupage):
    """Couche de graphiques : un camembert par agence, découpé selon un second axe."""
    couche = couche_points(valeur, "'%s'" % BLEU_NUIT, "''", etiquettes=True)
    couche["type"] = "ChartLayer"
    couche["chartType"] = "pieChart"
    couche["color"].update(
        {"auto": True, "mode": "byDimension", "dimensionScheme": "12", "opacity": 1}
    )
    couche["size"] = {
        "radiusMin": 10,
        "radiusMax": 34,
        "radiusValueMin": 0,
        "radiusValueMax": 1,
        "autoRadiusValueRange": True,
        "expression": {
            "key": "",
            "label": "",
            "type": "",
            "qNumFormat": {"qType": "U"},
        },
        "label": "",
        "slider": [10, 34],
        "sliderSingle": 24,
        "barHeight": 100,
        "barWidth": 20,
        "formatting": {"qNumFormat": {"qType": "U"}},
    }
    couche["tooltip"] = {"auto": True}
    couche["displayLegend"] = "auto"
    agence = couche["qHyperCubeDef"]["qDimensions"][0]
    agence["qAttributeExpressions"] = [
        {"qExpression": "[Point agence]", "id": "locationOrLatitude"},
        {"qExpression": "Agence", "id": "label"},
    ]
    couche["qHyperCubeDef"]["qDimensions"] = [
        agence,
        dimension(decoupage, decoupage, sans_vide=True),
    ]
    couche["qHyperCubeDef"]["qMeasures"] = [mesure(valeur, libelle, ("# ##0 k€", 0))]
    couche["qHyperCubeDef"]["qInitialDataFetch"] = [
        {"qLeft": 0, "qTop": 0, "qWidth": 3, "qHeight": 1000}
    ]
    return couche


def carte(titre, sous_titre, couches, fond="default"):
    o = objet("map", titre, sous_titre)
    p = o["qProperty"]
    p.pop("qUndoExclude", None)
    p["gaLayers"] = couches
    p["mapSettings"]["baseMap"] = fond
    p["mapSettings"]["initialView"] = {
        "center": [46.6, 2.5],
        "resolution": 4200,
        "bounds": {"min": [42.5, -4.8], "max": [51.1, 8.3]},
    }
    return o


def agences():
    ecart = ecart_pct(AG_CA, AG_CA_B)
    ecart_ke = "((%s) - (%s)) / 1000" % (AG_CA, AG_CA_B)
    taux = "(%s) / (%s)" % (AG_MB, AG_CA)
    sous_budget = "Sum(Aggr(If((%s) < (%s), 1, 0), Agence))" % (AG_CA, AG_CA_B)
    cartes = [
        carte_kpi(
            "Agences",
            "Dans le périmètre sélectionné",
            "Count({<Source={'Agences'}>} DISTINCT Agence)",
            F_ENTIER,
            taille="L",
        ),
        carte_kpi(
            "Chiffre d'affaires des agences",
            "Réel, " + PERIODE,
            "(%s) / 1000000" % AG_CA,
            F_ME,
            (ecart, "vs budget", F_ECART, True),
        ),
        carte_kpi(
            "Écart au budget",
            "Réel moins budget",
            ecart_ke,
            ("+# ##0 k€;-# ##0 k€", 0),
            (ecart, "du budget", F_ECART, True),
        ),
        carte_kpi(
            "Agences sous le budget",
            "Chiffre d'affaires réel inférieur au budget",
            sous_budget,
            F_ENTIER,
            taille="L",
        ),
    ]

    couleur_ecart = "ColorMix2(RangeMax(-1, RangeMin(1, (%s) / 0.08)), %s, %s, %s)" % (
        ecart,
        rvb(ROUGE),
        rvb(VERT),
        rvb(SABLE),
    )
    bulle = (
        "'CA réel : ' & Num((%s) / 1000, '# ##0 k€') & Chr(10) & "
        "'Écart au budget : ' & Num(%s, '+0,0 %%;-0,0 %%') & Chr(10) & "
        "'Taux de marge : ' & Num(%s, '0,0 %%')" % (AG_CA, ecart, taux)
    )
    vue_ecart = carte(
        "Vue écart au budget",
        "Taille : chiffre d'affaires réel · couleur : du rouge (sous le budget) au vert",
        [couche_points(AG_CA, couleur_ecart, bulle)],
    )
    couleur_marge = (
        "ColorMix1(RangeMax(0, RangeMin(1, ((%s) - 0.24) / 0.12)), %s, %s)"
        % (taux, rvb(SABLE), rvb(BLEU_NUIT))
    )
    vue_marge = carte(
        "Vue rentabilité",
        "Taille : marge brute réelle · couleur : plus le bleu est foncé, plus le taux est élevé",
        [couche_points(AG_MB, couleur_marge, bulle)],
        fond="pale",
    )

    vue_activite = carte(
        "Vue activité",
        "Un camembert par agence : sa taille suit le chiffre d'affaires, ses parts les BU",
        [couche_secteurs("(%s) / 1000" % AG_CA, "CA réel", "BU")],
        fond="pale",
    )
    vue_marge["qProperty"]["mapSettings"]["baseMap"] = "dark"

    classement = barres(
        "Écart de chiffre d'affaires par agence",
        "Réel moins budget, en k€",
        [dimension("Agence", "Agence", sans_vide=True)],
        [mesure(ecart_ke, "Écart")],
        horizontal=True,
        tri=0,
        etiquettes=False,
    )
    colorer_par_expression(classement, couleur_signe(ecart_ke))

    detail = tableau(
        "Détail par région et agence",
        "Montants en k€",
        [
            dimension("Région", "Région", sans_vide=True),
            dimension("Agence", "Agence", sans_vide=True),
        ],
        [
            mesure("(%s) / 1000" % AG_CA, "CA réel"),
            mesure("(%s) / 1000" % AG_CA_B, "CA budget"),
            mesure(ecart_ke, "Écart"),
            mesure(ecart, "Écart %", F_ECART),
            mesure(taux, "Taux de marge", F_PCT),
        ],
        tri=0,
    )

    return feuille(
        2,
        "Les agences sur la carte : écart au budget, rentabilité et activité par BU.",
        cartes,
        [
            (vue_ecart, 0, 8.5, 8, 9.5),
            (vue_marge, 8, 8.5, 8, 9.5),
            (vue_activite, 16, 8.5, 8, 9.5),
            (classement, 0, 18, 9, 6),
            (detail, 9, 18, 15, 6),
        ],
    )


# ---------------------------------------------------------------- 4. Écarts et résultat
RUBRIQUES = [
    # libellé, rang dans le compte de résultat, solde ?
    ("Chiffre d'affaires", 1, False),
    ("Coût des ventes", 2, False),
    ("MARGE BRUTE", 2, True),
    ("Frais de personnel", 3, False),
    ("Marketing & commercial", 4, False),
    ("Logistique & transport", 5, False),
    ("Loyers & frais généraux", 6, False),
    ("IT & systèmes", 7, False),
    ("EBITDA", 7, True),
    ("Dotations aux amortissements", 8, False),
    ("RÉSULTAT D'EXPLOITATION", 8, True),
]


def ligne_resultat(modele_expression):
    """Une expression par ligne du compte de résultat, choisie selon la ligne affichée."""
    libelles = ", ".join("'%s'" % lib.replace("'", "''") for lib, _, _ in RUBRIQUES)
    lignes = ", ".join(
        modele_expression(rang, "<=" if est_solde else "=")
        for _, rang, est_solde in RUBRIQUES
    )
    return "Pick(Match(ValueList(%s), %s), %s)" % (libelles, libelles, lignes), libelles


COURT = {
    "Chiffre d'affaires": "CA",
    "Coût des ventes": "Coût ventes",
    "Frais de personnel": "Personnel",
    "Marketing & commercial": "Marketing",
    "Logistique & transport": "Logistique",
    "Loyers & frais généraux": "Loyers",
    "IT & systèmes": "IT",
}


def ecarts():
    def tuile_solde(titre, rang):
        reel, budget, n1 = (
            solde("Réel", rang),
            solde("Budget", rang),
            solde("N-1", rang),
        )
        return carte_kpi(
            titre,
            "Réel, " + PERIODE,
            "(%s) / 1000000" % reel,
            F_ME,
            (ecart_pct(reel, budget), "vs budget", F_ECART, True),
            pied_n1(reel, n1),
        )

    cartes = [
        tuile_solde("Chiffre d'affaires", 1),
        tuile_solde("Marge brute", 2),
        tuile_solde("EBITDA", 7),
        tuile_solde("Résultat d'exploitation", 8),
    ]

    pont = cascade(
        "De la marge brute budget à la marge brute réelle",
        "Ce qui explique l'écart : volumes vendus, prix de vente, coûts d'achat (k€)",
        [
            ("Budget", "(%s) / 1000" % MB_B),
            ("Volume", "(%s) / 1000" % somme("Effet volume & mix")),
            ("Prix", "(%s) / 1000" % somme("Effet prix")),
            ("Coûts", "(%s) / 1000" % somme("Effet coûts d'achat")),
        ],
        "Réel",
    )
    # l'axe démarre sous la plus petite des deux marges : les effets restent lisibles
    pont["qProperty"]["measureAxis"].update(
        {
            "autoMinMax": False,
            "minMax": "min",
            "min": {
                "qValueExpression": {
                    "qExpr": "Floor(RangeMin(%s, %s) / 1000000 - 1) * 1000" % (MB, MB_B)
                }
            },
        }
    )

    effets = barres(
        "Effets volume, prix et coûts d'achat par BU",
        "Contribution de chaque effet à l'écart de marge, en k€",
        [dimension("BU", "BU", sans_vide=True)],
        [
            mesure("(%s) / 1000" % somme("Effet volume & mix"), "Volume et mix"),
            mesure("(%s) / 1000" % somme("Effet prix"), "Prix de vente"),
            mesure("(%s) / 1000" % somme("Effet coûts d'achat"), "Coûts d'achat"),
        ],
        etiquettes=False,
    )
    couleurs_mesures(effets, [BLEU_NUIT, SARCELLE, AMBRE])

    def colonne(colonne_cr):
        return lambda rang, signe: "(%s) / 1000" % solde(colonne_cr, rang, signe)

    reel, libelles = ligne_resultat(colonne("Réel"))
    budget, _ = ligne_resultat(colonne("Budget"))
    n1, _ = ligne_resultat(colonne("N-1"))
    ecart_valeur, _ = ligne_resultat(
        lambda rang, signe: (
            "((%s) - (%s)) / 1000"
            % (solde("Réel", rang, signe), solde("Budget", rang, signe))
        )
    )
    ecart_relatif, _ = ligne_resultat(
        lambda rang, signe: (
            "((%s) - (%s)) / Fabs(%s)"
            % (
                solde("Réel", rang, signe),
                solde("Budget", rang, signe),
                solde("Budget", rang, signe),
            )
        )
    )
    soldes = ", ".join("'%s'" % lib.replace("'", "''") for lib, _, s in RUBRIQUES if s)
    fond = "If(Match(ValueList(%s), %s), '%s')" % (libelles, soldes, FOND_SOLDE)
    rubrique = dimension("=ValueList(%s)" % libelles, "Rubrique")
    rubrique["qDef"]["autoSort"] = False
    rubrique["qDef"]["qSortCriterias"] = [{"qSortByLoadOrder": 1, "qExpression": {}}]
    rubrique["qAttributeExpressions"] = [
        {"qExpression": fond, "id": "cellBackgroundColor"}
    ]
    resultat = tableau(
        "Compte de résultat analytique",
        "En k€, " + PERIODE + " · les soldes intermédiaires sont surlignés",
        [rubrique],
        [
            mesure(reel, "Réel", fond=fond),
            mesure(budget, "Budget", fond=fond),
            mesure(ecart_valeur, "Écart", ("+# ##0;-# ##0", 0), fond=fond),
            mesure(ecart_relatif, "Écart %", F_ECART, fond=fond),
            mesure(n1, "Réel N-1", fond=fond),
        ],
        totaux=False,
    )

    contributions = cascade(
        "Écart d'EBITDA au budget",
        "Contribution de chaque rubrique, réel moins budget, en k€",
        [
            (
                COURT.get(libelle, libelle),
                "((%s) - (%s)) / 1000"
                % (solde("Réel", rang, "="), solde("Budget", rang, "=")),
            )
            for libelle, rang, est_solde in RUBRIQUES
            if not est_solde and rang <= 7
        ],
        "Écart",
    )

    return feuille(
        3,
        "Effets volume, prix et coûts d'achat ; compte de résultat et soldes.",
        cartes,
        [
            (pont, 0, 8.5, 12, 7.5),
            (effets, 12, 8.5, 12, 7.5),
            (resultat, 0, 16, 13, 8),
            (contributions, 13, 16, 11, 8),
        ],
    )


# ---------------------------------------------------------------- 5. BFR et trésorerie
def bfr():
    def fin(champ, ensemble=FIN, agregat="Sum"):
        return "%s(%s [%s])" % (agregat, ensemble, champ)

    def delai(nom, hausse_favorable):
        reel = fin("%s (jours)" % nom, agregat="Avg")
        objectif = fin("%s Objectif (jours)" % nom, agregat="Avg")
        n1 = fin("%s (jours)" % nom, FIN_N1, "Avg")
        return carte_kpi(
            nom + " moyen",
            "Moyenne des BU, dernier mois clôturé",
            reel,
            F_JOURS,
            (
                "(%s) - (%s)" % (reel, objectif),
                "vs objectif",
                ("+0,0 j;-0,0 j", 1),
                hausse_favorable,
            ),
            "'vs N-1 : ' & Num((%s) - (%s), '+0,0;-0,0') & ' j'" % (reel, n1),
        )

    bfr_reel, bfr_objectif = fin("BFR"), fin("BFR Objectif")
    tresorerie, tresorerie_n1 = (
        fin("Trésorerie fin de mois"),
        fin("Trésorerie fin de mois", FIN_N1),
    )
    plus_90 = "Sum({<Tranche={'Plus de 90 jours'}>} [Montant TTC])"
    cartes = [
        carte_kpi(
            "BFR",
            "À la fin du dernier mois clôturé",
            "(%s) / 1000000" % bfr_reel,
            F_ME,
            (ecart_pct(bfr_reel, bfr_objectif), "vs objectif", F_ECART, False),
            pied_n1(bfr_reel, fin("BFR", FIN_N1)),
        ),
        delai("DSO", False),
        delai("DIO", False),
        delai("DPO", True),
        carte_kpi(
            "Trésorerie disponible",
            "À la fin du dernier mois clôturé",
            "(%s) / 1000000" % tresorerie,
            F_ME,
            (ecart_pct(tresorerie, tresorerie_n1), "vs N-1", F_ECART, True),
        ),
        carte_kpi(
            "Créances à plus de 90 jours",
            "Balance âgée au 31/10/2026",
            "(%s) / 1000000" % plus_90,
            F_ME,
            (
                "-(%s) / Sum([Montant TTC])" % plus_90,
                "de l'encours clients",
                ("0,0 %;0,0 %", 1),
                True,
            ),
        ),
    ]

    dso = courbes(
        "DSO par BU",
        "Délai moyen de règlement des clients, en jours",
        [MOIS()],
        [mesure("Avg(%s [DSO (jours)])" % ANNEE, "DSO", F_DECIMAL)],
    )
    series_par_bu(dso, "Avg(%s [DSO (jours)])" % ANNEE, F_DECIMAL)
    suivi_bfr = courbes(
        "BFR réel contre objectif",
        "Fin de mois, en k€",
        [MOIS()],
        [
            mesure("Sum(%s BFR) / 1000" % ANNEE, "Réel"),
            mesure("Sum(%s [BFR Objectif]) / 1000" % ANNEE, "Objectif"),
        ],
    )
    couleurs_mesures(suivi_bfr, [BLEU_NUIT, AMBRE])
    suivi_tresorerie = courbes(
        "Trésorerie de fin de mois",
        "Depuis le début de l'historique, en k€",
        [dimension("Période", "Période", tri="numerique")],
        [mesure("Sum([Trésorerie fin de mois]) / 1000", "Trésorerie")],
    )
    couleurs_mesures(suivi_tresorerie, [BLEU_NUIT])
    suivi_tresorerie["qProperty"]["dataPoint"]["show"] = False

    balance = barres(
        "Balance âgée par tranche de retard",
        "Créances clients au 31/10/2026 par BU, en k€",
        [
            dimension(
                "=Dual(Tranche, [Ordre tranche])",
                "Tranche",
                tri="numerique",
                sans_vide=True,
            ),
        ],
        [mesure("Sum([Montant TTC]) / 1000", "Montant TTC")],
        groupement="stacked",
        etiquettes=False,
    )
    series_par_bu(
        balance, "Sum({<Source={'Créances clients'}>} [Montant TTC]) / 1000", F_ENTIER
    )
    echu = "Sum({<Échu={'Échu'}>} [Montant TTC]) / 1000"
    clients = barres(
        "Créances échues : les 15 clients les plus exposés",
        "Montant échu, en k€",
        [dimension("Client", "Client", sans_vide=True, limite=15)],
        [mesure(echu, "Montant échu")],
        horizontal=True,
        tri=0,
    )
    colorer_par_expression(clients, "'%s'" % CORAIL)

    return feuille(
        4,
        "BFR, délais DSO, DIO, DPO, trésorerie et créances clients échues.",
        cartes,
        [
            (dso, 0, 8.5, 8, 7.5),
            (suivi_bfr, 8, 8.5, 8, 7.5),
            (suivi_tresorerie, 16, 8.5, 8, 7.5),
            (balance, 0, 16, 11, 8),
            (clients, 11, 16, 13, 8),
        ],
    )


# ---------------------------------------------------------------- écriture
def apparence():
    """Thème de l'application et bandeau de titre aux couleurs de la charte."""
    return {
        "qInfo": {"qId": "orv-apparence", "qType": "appprops"},
        "qMetaDef": {},
        "sheetTitleBgColor": BLEU_NUIT,
        "sheetTitleGradientColor": BLEU_NUIT,
        "sheetTitleColor": "#ffffff",
        "sheetLogoThumbnail": {"qStaticContentUrlDef": {}},
        "sheetLogoPosition": "",
        "rtl": False,
        "theme": "breeze",
        "disableCellNavMenu": False,
        "disableCellContextMenu": False,
        "chartAnimations": True,
        "defaultSheet": FEUILLES[0][0],
    }


def ecrire(nom, contenu):
    chemin = os.path.join(SORTIE, nom + ".json")
    with io.open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(json.dumps(contenu, ensure_ascii=False, indent=1))
    return chemin


if __name__ == "__main__":
    if not os.path.isdir(SORTIE):
        os.makedirs(SORTIE)
    ecrire("00_apparence", apparence())
    constructeurs = [synthese, ca_marge, agences, ecarts, bfr]
    for rang, construire in enumerate(constructeurs):
        contenu = construire()
        nom = "%02d_%s" % (rang + 1, FEUILLES[rang][0].replace("orv-", ""))
        ecrire(nom, contenu)
        print("%s : %d objets" % (nom, len(contenu["qChildren"])))
    dossier_mesures = os.path.join(ICI, "mesures")
    if not os.path.isdir(dossier_mesures):
        os.makedirs(dossier_mesures)
    for definition in BIBLIOTHEQUE:
        ecrire(os.path.join("..", "mesures", definition["qInfo"]["qId"]), definition)
    print("%d mesures de bibliothèque" % len(BIBLIOTHEQUE))
