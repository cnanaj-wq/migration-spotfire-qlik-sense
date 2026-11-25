"""Jeu de données FICTIF de contrôle de gestion pour un dashboard Spotfire.

Société inventée : « Orvane Distribution » (distribution B2B d'équipements du bâtiment).
Toute ressemblance avec une entreprise ou un client réel serait fortuite.

Sorties (dossier data/) : ventes, ecarts_marge, compte_resultat, bfr, tresorerie,
creances_clients — en CSV (UTF-8, virgule, point décimal) et dans un classeur Excel.
Les tables se recoupent : le CA et le coût des ventes du compte de résultat sont la
somme exacte des ventes, les écarts de marge somment à (marge réelle - marge budget),
la balance âgée somme aux créances clients du dernier mois clôturé.
"""

import csv
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

random.seed(20261125)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)


def lire_parametres():
    """Lit parametres/parametres.xlsx : une liste de dictionnaires par feuille."""
    from openpyxl import load_workbook

    chemin = Path(__file__).parent / "parametres" / "parametres.xlsx"
    if not chemin.exists():
        raise SystemExit(f"{chemin} introuvable : lance d'abord creer_parametres.py")
    feuilles = {}
    for ws in load_workbook(chemin, read_only=True, data_only=True).worksheets:
        lignes = [
            l for l in ws.iter_rows(values_only=True) if any(c is not None for c in l)
        ]
        feuilles[ws.title] = [dict(zip(lignes[0], l)) for l in lignes[1:]]
    return feuilles


PARAMETRES = lire_parametres()
GENERAL = {l["Clé"]: l["Valeur"] for l in PARAMETRES["Général"]}

ANNEES = [2024, 2025, 2026]
# réel disponible jusqu'à ce mois (feuille Général du classeur de paramètres)
DERNIER_MOIS_CLOS = tuple(int(x) for x in str(GENERAL["dernier_mois_clos"]).split("-"))
TVA = 1.20

# BU, produit, prix de vente budget 2026, coût unitaire budget 2026, poids dans la BU, saisonnalité
S_STD = [0.95, 0.95, 1.05, 1.00, 1.00, 1.05, 0.95, 0.70, 1.10, 1.10, 1.10, 1.05]
S_CHAUF = [1.20, 1.10, 0.95, 0.80, 0.70, 0.65, 0.60, 0.50, 1.10, 1.40, 1.50, 1.50]
S_CLIM = [0.50, 0.55, 0.80, 1.10, 1.50, 1.90, 1.80, 1.00, 0.80, 0.70, 0.65, 0.70]
S_MAINT = [1.40, 1.00, 0.95, 0.90, 0.90, 0.90, 0.80, 0.70, 1.30, 1.10, 1.05, 1.00]
S_DEPAN = [1.40, 1.30, 1.00, 0.85, 0.75, 0.80, 0.85, 0.70, 0.90, 1.05, 1.15, 1.25]

CA_BU = {
    "Outillage": 18.0e6,
    "Électricité": 22.0e6,
    "Chauffage & Climatisation": 32.0e6,
    "Services": 13.0e6,
}
PRODUITS = [
    ("Outillage", "Perceuse-visseuse pro", 189, 121, 0.45, S_STD),
    ("Outillage", "Coffret outillage à main", 95, 58, 0.30, S_STD),
    ("Outillage", "Consommables & abrasifs", 24, 13, 0.25, S_STD),
    ("Électricité", "Tableau électrique", 310, 214, 0.40, S_STD),
    ("Électricité", "Câbles & gaines", 68, 49, 0.35, S_STD),
    ("Électricité", "Éclairage LED", 42, 25, 0.25, S_STD),
    ("Chauffage & Climatisation", "Pompe à chaleur", 4200, 3150, 0.45, S_CHAUF),
    (
        "Chauffage & Climatisation",
        "Chaudière à condensation",
        2600,
        1980,
        0.30,
        S_CHAUF,
    ),
    ("Chauffage & Climatisation", "Climatiseur réversible", 1450, 1060, 0.25, S_CLIM),
    ("Services", "Contrat de maintenance", 780, 390, 0.40, S_MAINT),
    ("Services", "Installation", 1250, 760, 0.42, S_STD),
    ("Services", "Dépannage", 210, 118, 0.18, S_DEPAN),
]
REGIONS = {
    "Île-de-France": 0.30,
    "Sud-Est": 0.24,
    "Ouest": 0.18,
    "Nord-Est": 0.16,
    "Sud-Ouest": 0.12,
}
CANAUX = {"Agences": 0.55, "Grands comptes": 0.30, "E-commerce": 0.15}
CANAUX_SERVICES = {"Agences": 0.60, "Grands comptes": 0.38, "E-commerce": 0.02}
INDICE_PRIX_CANAL = {"Agences": 1.00, "Grands comptes": 0.93, "E-commerce": 0.96}
CROISSANCE_BUDGET = {2024: 1.00, 2025: 1.04, 2026: 1.10}
INDICE_PRIX_AN = {2024: 0.95, 2025: 0.98, 2026: 1.00}
INDICE_COUT_AN = {2024: 0.94, 2025: 0.975, 2026: 1.00}


def clos(an, mois):
    return (an, mois) <= DERNIER_MOIS_CLOS


def bruit(sigma):
    return math.exp(random.gauss(0, sigma))


def r2(x):
    return None if x is None else round(x, 2)


# ---------------------------------------------------------------- ventes
def facteurs_reel(an, mois, bu, region, canal):
    """Écarts réel / budget : c'est ici que se trouve l'histoire racontée par le dashboard."""
    vol, prix, cout = 1.0, 1.0, 1.0
    if an == 2024:
        vol = 0.99
    elif an == 2025:
        vol = 1.01
    else:
        if region == "Sud-Ouest":
            vol *= 0.90  # région en retard sur son budget
        if canal == "E-commerce":
            vol *= 1.18  # le digital sur-performe…
            prix *= 0.97  # …mais avec des prix plus bas
        if canal == "Grands comptes":
            prix *= 0.99
        if bu == "Services":
            vol *= 1.08
            cout *= 1.01
        if bu == "Outillage":
            vol *= 0.96
        if bu == "Électricité":
            cout *= 1.02
        if bu == "Chauffage & Climatisation":
            vol *= 0.97
            prix *= 1.025  # hausse tarifaire partielle
            cout *= (
                1.03 + 0.05 * (mois - 1) / 9
            )  # inflation fournisseurs qui s'accélère
    return vol, prix, cout


ventes = {}
for an in ANNEES:
    for mois in range(1, 13):
        for bu, produit, pv, cu, poids, saison in PRODUITS:
            qte_an = CA_BU[bu] * poids / pv
            canaux = CANAUX_SERVICES if bu == "Services" else CANAUX
            for region, wr in REGIONS.items():
                for canal, wc in canaux.items():
                    qb = max(
                        1,
                        round(
                            qte_an
                            * wr
                            * wc
                            * saison[mois - 1]
                            / 12
                            * CROISSANCE_BUDGET[an]
                        ),
                    )
                    pb = pv * INDICE_PRIX_CANAL[canal] * INDICE_PRIX_AN[an]
                    cb = cu * INDICE_COUT_AN[an]
                    lig = {
                        "qb": qb,
                        "pb": pb,
                        "cb": cb,
                        "qr": None,
                        "pr": None,
                        "cr": None,
                    }
                    if clos(an, mois):
                        fv, fp, fc = facteurs_reel(an, mois, bu, region, canal)
                        lig["qr"] = max(0, round(qb * fv * bruit(0.08)))
                        lig["pr"] = pb * fp * bruit(0.01)
                        lig["cr"] = cb * fc * bruit(0.015)
                    ventes[(an, mois, bu, produit, region, canal)] = lig

# ratio réel/budget cumulé 2026 par (produit, région, canal) pour la prévision d'atterrissage
cum = defaultdict(lambda: [0.0, 0.0])
for (an, mois, bu, produit, region, canal), l in ventes.items():
    if an == 2026 and clos(an, mois):
        cum[(produit, region, canal)][0] += l["qr"] * l["pr"]
        cum[(produit, region, canal)][1] += l["qb"] * l["pb"]

lignes_ventes = []
agg_pnl = defaultdict(lambda: defaultdict(float))  # (an, mois, bu) -> mesures
agg_ecarts = defaultdict(lambda: defaultdict(float))  # (an, mois, bu, region) -> postes
for (an, mois, bu, produit, region, canal), l in ventes.items():
    n1 = ventes.get((an - 1, mois, bu, produit, region, canal))
    ca_b, cv_b = l["qb"] * l["pb"], l["qb"] * l["cb"]
    reel = l["qr"] is not None
    ca_r = l["qr"] * l["pr"] if reel else None
    cv_r = l["qr"] * l["cr"] if reel else None
    if reel:
        ca_p, cv_p = ca_r, cv_r
    else:
        a, b = cum[(produit, region, canal)]
        k = min(1.15, max(0.85, a / b if b else 1.0))
        ca_p, cv_p = ca_b * k, cv_b * k * 1.02
    ca_n1 = n1["qr"] * n1["pr"] if n1 and n1["qr"] is not None else None
    cv_n1 = n1["qr"] * n1["cr"] if n1 and n1["qr"] is not None else None
    e_vol = (l["qr"] - l["qb"]) * (l["pb"] - l["cb"]) if reel else None
    e_prix = (l["pr"] - l["pb"]) * l["qr"] if reel else None
    e_cout = -(l["cr"] - l["cb"]) * l["qr"] if reel else None
    # arrondis ligne à ligne, puis agrégats calculés sur les valeurs arrondies (recoupement exact)
    ca_r, ca_b, ca_n1, ca_p = r2(ca_r), r2(ca_b), r2(ca_n1), r2(ca_p)
    cv_r, cv_b, cv_n1, cv_p = r2(cv_r), r2(cv_b), r2(cv_n1), r2(cv_p)
    e_vol, e_prix = r2(e_vol), r2(e_prix)
    if reel:
        e_cout = r2((ca_r - cv_r) - (ca_b - cv_b) - e_vol - e_prix)
    lignes_ventes.append(
        {
            "Date": date(an, mois, 1).isoformat(),
            "Exercice": an,
            "Mois": mois,
            "Statut": "Réel" if reel else "Prévision",
            "BU": bu,
            "Produit": produit,
            "Région": region,
            "Canal": canal,
            "Quantité Réel": l["qr"],
            "Quantité Budget": l["qb"],
            "Quantité N-1": n1["qr"] if n1 else None,
            "CA Réel": ca_r,
            "CA Budget": ca_b,
            "CA N-1": ca_n1,
            "CA Prévision": ca_p,
            "Coût des ventes Réel": cv_r,
            "Coût des ventes Budget": cv_b,
            "Coût des ventes N-1": cv_n1,
            "Coût des ventes Prévision": cv_p,
            "Marge brute Réel": r2(ca_r - cv_r) if reel else None,
            "Marge brute Budget": r2(ca_b - cv_b),
            "Marge brute N-1": r2(ca_n1 - cv_n1) if ca_n1 is not None else None,
            "Marge brute Prévision": r2(ca_p - cv_p),
            "Effet volume & mix": e_vol,
            "Effet prix": e_prix,
            "Effet coûts d'achat": e_cout,
        }
    )
    p = agg_pnl[(an, mois, bu)]
    for nom, v in (
        ("ca_r", ca_r),
        ("ca_b", ca_b),
        ("ca_n1", ca_n1),
        ("ca_p", ca_p),
        ("cv_r", cv_r),
        ("cv_b", cv_b),
        ("cv_n1", cv_n1),
        ("cv_p", cv_p),
    ):
        if v is not None:
            p[nom] += v
    if reel:
        e = agg_ecarts[(an, mois, bu, region)]
        e["Marge brute Budget"] += ca_b - cv_b
        e["Effet volume & mix"] += e_vol
        e["Effet prix"] += e_prix
        e["Effet coûts d'achat"] += e_cout

# ---------------------------------------------------------------- écarts de marge (format long, pour la cascade)
POSTES = [
    ("Marge brute Budget", 1, "Base"),
    ("Effet volume & mix", 2, "Effet"),
    ("Effet prix", 3, "Effet"),
    ("Effet coûts d'achat", 4, "Effet"),
]
lignes_ecarts = []
for (an, mois, bu, region), e in sorted(agg_ecarts.items()):
    for poste, ordre, typ in POSTES:
        lignes_ecarts.append(
            {
                "Date": date(an, mois, 1).isoformat(),
                "Exercice": an,
                "Mois": mois,
                "BU": bu,
                "Région": region,
                "Ordre": ordre,
                "Poste": poste,
                "Type": typ,
                "Montant": r2(e[poste]),
            }
        )

# ---------------------------------------------------------------- compte de résultat analytique
# charges d'exploitation budgétées en % du CA budget annuel de la BU
OPEX = {  # rubrique: (ordre, {bu: %CA}, part variable avec l'activité)
    "Frais de personnel": (
        3,
        {
            "Outillage": 0.115,
            "Électricité": 0.105,
            "Chauffage & Climatisation": 0.085,
            "Services": 0.215,
        },
        0.0,
    ),
    "Marketing & commercial": (
        4,
        {
            "Outillage": 0.035,
            "Électricité": 0.025,
            "Chauffage & Climatisation": 0.022,
            "Services": 0.020,
        },
        0.3,
    ),
    "Logistique & transport": (
        5,
        {
            "Outillage": 0.050,
            "Électricité": 0.045,
            "Chauffage & Climatisation": 0.042,
            "Services": 0.012,
        },
        1.0,
    ),
    "Loyers & frais généraux": (
        6,
        {
            "Outillage": 0.028,
            "Électricité": 0.025,
            "Chauffage & Climatisation": 0.020,
            "Services": 0.028,
        },
        0.0,
    ),
    "IT & systèmes": (
        7,
        {
            "Outillage": 0.012,
            "Électricité": 0.012,
            "Chauffage & Climatisation": 0.010,
            "Services": 0.016,
        },
        0.0,
    ),
    "Dotations aux amortissements": (
        8,
        {
            "Outillage": 0.020,
            "Électricité": 0.020,
            "Chauffage & Climatisation": 0.016,
            "Services": 0.024,
        },
        0.0,
    ),
}
DERIVE_2026 = {
    "Frais de personnel": 0.97,
    "Marketing & commercial": 1.03,
    "Logistique & transport": 1.11,
    "Loyers & frais généraux": 1.01,
    "IT & systèmes": 1.04,
    "Dotations aux amortissements": 1.00,
}
AGREGAT = {
    1: "Marge brute",
    2: "Marge brute",
    3: "EBITDA",
    4: "EBITDA",
    5: "EBITDA",
    6: "EBITDA",
    7: "EBITDA",
    8: "Résultat d'exploitation",
}

ca_b_an = defaultdict(float)
for (an, mois, bu), p in agg_pnl.items():
    ca_b_an[(an, bu)] += p["ca_b"]

opex = {}  # (an, mois, bu, rubrique) -> {b, r}
for an in ANNEES:
    for bu in CA_BU:
        for rub, (ordre, pct, part_var) in OPEX.items():
            annuel = ca_b_an[(an, bu)] * pct[bu]
            for mois in range(1, 13):
                p = agg_pnl[(an, mois, bu)]
                poids_var = p["ca_b"] / ca_b_an[(an, bu)]
                b = annuel * ((1 - part_var) / 12 + part_var * poids_var)
                r = None
                if clos(an, mois):
                    derive = (
                        DERIVE_2026[rub]
                        if an == 2026
                        else random.choice([0.99, 1.0, 1.01])
                    )
                    activite = 1 + part_var * (p["ca_r"] / p["ca_b"] - 1)
                    r = b * derive * activite * bruit(0.02 if ordre != 8 else 0.003)
                opex[(an, mois, bu, rub)] = {"b": r2(b), "r": r2(r)}

cum_opex = defaultdict(lambda: [0.0, 0.0])
for (an, mois, bu, rub), v in opex.items():
    if an == 2026 and v["r"] is not None:
        cum_opex[(bu, rub)][0] += v["r"]
        cum_opex[(bu, rub)][1] += v["b"]

lignes_pnl = []
pnl_mois = defaultdict(
    lambda: defaultdict(float)
)  # (an, mois, bu) -> ebitda_r, rex_r, ...


def ajoute_pnl(an, mois, bu, ordre, rubrique, nature, reel, budget, n1, prev):
    lignes_pnl.append(
        {
            "Date": date(an, mois, 1).isoformat(),
            "Exercice": an,
            "Mois": mois,
            "Statut": "Réel" if clos(an, mois) else "Prévision",
            "BU": bu,
            "Ordre": ordre,
            "Rubrique": rubrique,
            "Nature": nature,
            "Agrégat": AGREGAT[ordre],
            "Réel": r2(reel),
            "Budget": r2(budget),
            "N-1": r2(n1),
            "Prévision": r2(prev),
        }
    )
    m = pnl_mois[(an, mois, bu)]
    if ordre <= 7:
        if reel is not None:
            m["ebitda_r"] += reel
        m["ebitda_b"] += budget
    if reel is not None:
        m["rex_r"] += reel


for an in ANNEES:
    for mois in range(1, 13):
        for bu in CA_BU:
            p = agg_pnl[(an, mois, bu)]
            reel = clos(an, mois)
            a_n1 = an > ANNEES[0]
            ajoute_pnl(
                an,
                mois,
                bu,
                1,
                "Chiffre d'affaires",
                "Produits",
                p["ca_r"] if reel else None,
                p["ca_b"],
                p["ca_n1"] if a_n1 else None,
                p["ca_p"],
            )
            ajoute_pnl(
                an,
                mois,
                bu,
                2,
                "Coût des ventes",
                "Charges",
                -p["cv_r"] if reel else None,
                -p["cv_b"],
                -p["cv_n1"] if a_n1 else None,
                -p["cv_p"],
            )
            for rub, (ordre, _, _) in OPEX.items():
                v = opex[(an, mois, bu, rub)]
                n1 = opex.get((an - 1, mois, bu, rub))
                if v["r"] is not None:
                    prev = v["r"]
                else:
                    a, b = cum_opex[(bu, rub)]
                    prev = v["b"] * (a / b if b else 1.0)
                ajoute_pnl(
                    an,
                    mois,
                    bu,
                    ordre,
                    rub,
                    "Charges",
                    -v["r"] if v["r"] is not None else None,
                    -v["b"],
                    -n1["r"] if n1 and n1["r"] is not None else None,
                    -prev,
                )

# ---------------------------------------------------------------- BFR
JOURS = {  # bu: (DSO objectif, DIO objectif, DPO objectif, dérive DSO 2026, dérive DIO 2026)
    "Outillage": (42, 62, 52, 1, 0),
    "Électricité": (50, 55, 50, 10, 2),
    "Chauffage & Climatisation": (46, 48, 55, 5, 12),
    "Services": (38, 6, 35, 1, 0),
}
mois_clos = [(an, m) for an in ANNEES for m in range(1, 13) if clos(an, m)]
lignes_bfr, bfr_total, creances_fin = [], defaultdict(float), {}
for bu, (dso_o, dio_o, dpo_o, d_dso, d_dio) in JOURS.items():
    for i, (an, mois) in enumerate(mois_clos):
        fen = mois_clos[max(0, i - 2) : i + 1]
        ca_j = sum(agg_pnl[(a, m, bu)]["ca_r"] for a, m in fen) / (30 * len(fen))
        cv_j = sum(agg_pnl[(a, m, bu)]["cv_r"] for a, m in fen) / (30 * len(fen))
        av = (mois - 1) / 9 if an == 2026 else 0.0
        dso = dso_o + d_dso * av + random.uniform(-1.5, 1.5)
        dio = dio_o + d_dio * av + random.uniform(-1.5, 1.5)
        dpo = dpo_o + random.uniform(-2, 2)
        creances, stocks, dettes = dso * ca_j * TVA, dio * cv_j, dpo * cv_j * TVA
        bfr = creances + stocks - dettes
        bfr_obj = dso_o * ca_j * TVA + dio_o * cv_j - dpo_o * cv_j * TVA
        bfr_total[(an, mois)] += bfr
        if (an, mois) == DERNIER_MOIS_CLOS:
            creances_fin[bu] = round(creances, 2)
        lignes_bfr.append(
            {
                "Date": date(an, mois, 1).isoformat(),
                "Exercice": an,
                "Mois": mois,
                "BU": bu,
                "Créances clients": r2(creances),
                "Stocks": r2(stocks),
                "Dettes fournisseurs": r2(dettes),
                "BFR": r2(bfr),
                "BFR Objectif": r2(bfr_obj),
                "DSO (jours)": round(dso, 1),
                "DSO Objectif (jours)": dso_o,
                "DIO (jours)": round(dio, 1),
                "DIO Objectif (jours)": dio_o,
                "DPO (jours)": round(dpo, 1),
                "DPO Objectif (jours)": dpo_o,
                "CA journalier TTC": r2(ca_j * TVA),
                "Coût des ventes journalier": r2(cv_j),
            }
        )
lignes_bfr.sort(key=lambda x: (x["Date"], x["BU"]))

# ---------------------------------------------------------------- trésorerie (tableau de flux simplifié, niveau société)
lignes_treso, treso, bfr_prec = [], 8_500_000.0, None
for an, mois in mois_clos:
    ebitda = sum(pnl_mois[(an, mois, bu)]["ebitda_r"] for bu in CA_BU)
    rex = sum(pnl_mois[(an, mois, bu)]["rex_r"] for bu in CA_BU)
    ca = sum(agg_pnl[(an, mois, bu)]["ca_r"] for bu in CA_BU)
    var_bfr = 0.0 if bfr_prec is None else bfr_total[(an, mois)] - bfr_prec
    bfr_prec = bfr_total[(an, mois)]
    capex = ca * (0.035 if mois in (3, 9) else 0.012) * bruit(0.15)
    impots = max(0.0, rex) * 3 * 0.25 if mois in (3, 6, 9, 12) else 0.0
    flux = ebitda - var_bfr - capex - impots
    treso += flux
    lignes_treso.append(
        {
            "Date": date(an, mois, 1).isoformat(),
            "Exercice": an,
            "Mois": mois,
            "EBITDA": r2(ebitda),
            "Variation de BFR": r2(-var_bfr),
            "Investissements": r2(-capex),
            "Impôt sur les sociétés": r2(-impots),
            "Flux net de trésorerie": r2(flux),
            "Trésorerie fin de mois": r2(treso),
        }
    )

# ---------------------------------------------------------------- balance âgée (factures ouvertes au dernier mois clos)
ARRETE = (date(*DERNIER_MOIS_CLOS, 28) + timedelta(days=4)).replace(day=1) - timedelta(
    days=1
)
PREFIXES = [
    "Bâti",
    "Élec",
    "Therm",
    "Rénov",
    "Habitat",
    "Chantier",
    "Atelier",
    "Clim",
    "Pro",
    "Artisans",
]
SUFFIXES = [
    "Ouest",
    "Service",
    "Concept",
    "Solutions",
    "Réunis",
    "Atlantique",
    "du Midi",
    "& Fils",
    "Plus",
    "Expert",
    "Rhône",
    "Nord",
]
FORMES = ["SARL", "SAS", "SA"]
clients, noms = [], set()
while len(clients) < 60:
    nom = f"{random.choice(PREFIXES)} {random.choice(SUFFIXES)} {random.choice(FORMES)}"
    if nom in noms:
        continue
    noms.add(nom)
    canal = "Grands comptes" if len(clients) < 18 else "Agences"
    clients.append(
        {
            "nom": nom,
            "canal": canal,
            "region": random.choices(list(REGIONS), weights=list(REGIONS.values()))[0],
        }
    )
TRANCHES = [
    "Non échu",
    "1 à 30 jours",
    "31 à 60 jours",
    "61 à 90 jours",
    "Plus de 90 jours",
]
BORNES = [None, (1, 30), (31, 60), (61, 90), (91, 170)]
PROBA = {  # la dérive du DSO vient surtout des grands comptes en Électricité
    ("Agences", "std"): [0.66, 0.18, 0.09, 0.04, 0.03],
    ("Grands comptes", "std"): [0.58, 0.20, 0.11, 0.07, 0.04],
    ("Grands comptes", "Électricité"): [0.40, 0.22, 0.17, 0.12, 0.09],
    ("Grands comptes", "Chauffage & Climatisation"): [0.50, 0.22, 0.14, 0.09, 0.05],
}
lignes_fact, num = [], 1
tot_creances = sum(creances_fin.values())
for bu in CA_BU:
    n = round(900 * creances_fin[bu] / tot_creances)
    brut = []
    for _ in range(n):
        cl = random.choices(
            clients,
            weights=[4 if c["canal"] == "Grands comptes" else 1 for c in clients],
        )[0]
        proba = PROBA.get((cl["canal"], bu), PROBA[(cl["canal"], "std")])
        t = random.choices(range(5), weights=proba)[0]
        delai = (
            random.choice([45, 60])
            if cl["canal"] == "Grands comptes"
            else random.choice([30, 45])
        )
        if t == 0:
            retard = 0
            echeance = ARRETE + timedelta(days=random.randint(0, delai - 1))
        else:
            retard = random.randint(*BORNES[t])
            echeance = ARRETE - timedelta(days=retard)
        montant = random.lognormvariate(0, 0.9) * (
            2.2 if cl["canal"] == "Grands comptes" else 1.0
        )
        brut.append((cl, t, retard, echeance, delai, montant))
    echelle = creances_fin[bu] / sum(b[5] for b in brut)
    montants = [round(b[5] * echelle, 2) for b in brut]
    montants[-1] = round(
        montants[-1] + creances_fin[bu] - sum(montants), 2
    )  # recoupement au centime
    for (cl, t, retard, echeance, delai, _), mt in zip(brut, montants):
        lignes_fact.append(
            {
                "N° facture": f"FA-2026-{num:05d}",
                "Client": cl["nom"],
                "Canal": cl["canal"],
                "Région": cl["region"],
                "BU": bu,
                "Date facture": (echeance - timedelta(days=delai)).isoformat(),
                "Date échéance": echeance.isoformat(),
                "Délai de paiement (jours)": delai,
                "Montant TTC": mt,
                "Jours de retard": retard,
                "Ordre tranche": t + 1,
                "Tranche": TRANCHES[t],
                "Échu": "Échu" if t else "Non échu",
            }
        )
        num += 1

# ---------------------------------------------------------------- ventes par agence (pour la carte)
# Ventilation des ventes Région x BU sur 24 agences géolocalisées. Générateur aléatoire
# séparé : les autres tables restent identiques. Recoupement exact avec la table ventes.
rnd_ag = random.Random(20261126)
AGENCES = [  # ville, région, latitude, longitude, poids dans la région
    ("Paris", "Île-de-France", 48.8566, 2.3522, 0.34),
    ("Nanterre", "Île-de-France", 48.8924, 2.2069, 0.22),
    ("Créteil", "Île-de-France", 48.7904, 2.4556, 0.17),
    ("Versailles", "Île-de-France", 48.8049, 2.1204, 0.15),
    ("Cergy", "Île-de-France", 49.0364, 2.0761, 0.12),
    ("Lyon", "Sud-Est", 45.7640, 4.8357, 0.32),
    ("Marseille", "Sud-Est", 43.2965, 5.3698, 0.26),
    ("Nice", "Sud-Est", 43.7102, 7.2620, 0.15),
    ("Grenoble", "Sud-Est", 45.1885, 5.7245, 0.14),
    ("Montpellier", "Sud-Est", 43.6108, 3.8767, 0.13),
    ("Nantes", "Ouest", 47.2184, -1.5536, 0.30),
    ("Rennes", "Ouest", 48.1173, -1.6778, 0.24),
    ("Rouen", "Ouest", 49.4432, 1.0993, 0.18),
    ("Angers", "Ouest", 47.4784, -0.5632, 0.15),
    ("Brest", "Ouest", 48.3904, -4.4861, 0.13),
    ("Lille", "Nord-Est", 50.6292, 3.0573, 0.30),
    ("Strasbourg", "Nord-Est", 48.5734, 7.7521, 0.24),
    ("Metz", "Nord-Est", 49.1193, 6.1757, 0.17),
    ("Reims", "Nord-Est", 49.2583, 4.0317, 0.15),
    ("Dijon", "Nord-Est", 47.3220, 5.0415, 0.14),
    ("Bordeaux", "Sud-Ouest", 44.8378, -0.5792, 0.36),
    ("Toulouse", "Sud-Ouest", 43.6047, 1.4442, 0.34),
    ("Pau", "Sud-Ouest", 43.2951, -0.3708, 0.16),
    ("Limoges", "Sud-Ouest", 45.8336, 1.2611, 0.14),
]
# performance propre à chaque agence en 2026 (réel vs budget) : crée les points chauds de la carte
PERF_AGENCE = {a[0]: rnd_ag.uniform(0.94, 1.06) for a in AGENCES}
PERF_AGENCE.update(
    {"Toulouse": 0.88, "Pau": 0.90, "Lyon": 1.07, "Nantes": 1.06, "Metz": 0.92}
)
MESURES_AG = [
    "CA Réel",
    "CA Budget",
    "CA N-1",
    "CA Prévision",
    "Marge brute Réel",
    "Marge brute Budget",
    "Marge brute N-1",
    "Marge brute Prévision",
]
MESURES_REEL = {"CA Réel", "Marge brute Réel"}

agg_ag = defaultdict(lambda: dict.fromkeys(MESURES_AG))
for l in lignes_ventes:
    cle = (l["Date"], l["Exercice"], l["Mois"], l["Statut"], l["BU"], l["Région"])
    for m in MESURES_AG:
        if l[m] is not None:
            agg_ag[cle][m] = (agg_ag[cle][m] or 0.0) + l[m]

lignes_agences = []
for (d, an, mois, statut, bu, region), tot in sorted(agg_ag.items()):
    ags = [a for a in AGENCES if a[1] == region]
    parts = {m: [] for m in MESURES_AG}
    for m in MESURES_AG:
        if tot[m] is None:
            parts[m] = [None] * len(ags)
            continue
        poids = []
        for ville, _, _, _, w in ags:
            perf = PERF_AGENCE[ville] if (m in MESURES_REEL and an == 2026) else 1.0
            poids.append(w * perf * math.exp(rnd_ag.gauss(0, 0.03)))
        s = sum(poids)
        vals = [round(tot[m] * p / s, 2) for p in poids]
        vals[0] = round(
            vals[0] + round(tot[m], 2) - sum(vals), 2
        )  # recoupement au centime
        parts[m] = vals
    if statut == "Réel":  # sur un mois clôturé, la prévision est le réel
        parts["CA Prévision"] = parts["CA Réel"]
        parts["Marge brute Prévision"] = parts["Marge brute Réel"]
    for i, (ville, _, lat, lon, _) in enumerate(ags):
        lig = {
            "Date": d,
            "Exercice": an,
            "Mois": mois,
            "Statut": statut,
            "BU": bu,
            "Région": region,
            "Agence": ville,
            "Latitude": lat,
            "Longitude": lon,
        }
        lig.update({m: parts[m][i] for m in MESURES_AG})
        lignes_agences.append(lig)

# ---------------------------------------------------------------- écriture
TABLES = {
    "ventes_agences": lignes_agences,
    "ventes": lignes_ventes,
    "ecarts_marge": lignes_ecarts,
    "compte_resultat": lignes_pnl,
    "bfr": lignes_bfr,
    "tresorerie": lignes_treso,
    "creances_clients": lignes_fact,
    # tables de paramétrage recopiées telles quelles depuis le classeur de paramètres
    "securite": PARAMETRES["Sécurité"],
    "seuils": PARAMETRES["Seuils"],
}
for nom, lignes in TABLES.items():
    with open(OUT / f"{nom}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f"{nom:18s} {len(lignes):6d} lignes")

try:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for nom, lignes in TABLES.items():
        ws = wb.create_sheet(nom)
        cols = list(lignes[0])
        ws.append(cols)
        for l in lignes:
            ws.append(
                [
                    date.fromisoformat(l[c]) if c.startswith("Date") else l[c]
                    for c in cols
                ]
            )
    wb.save(OUT / "controle_gestion_orvane.xlsx")
    print("Classeur Excel écrit")
except ImportError:
    print("openpyxl absent : CSV uniquement")


# ---------------------------------------------------------------- contrôles de cohérence
def somme(lignes, col, **filtre):
    return sum(l[col] or 0 for l in lignes if all(l[k] == v for k, v in filtre.items()))


print("\n--- Contrôles ---")
for an in ANNEES:
    ca_v = somme(lignes_ventes, "CA Réel", Exercice=an)
    ca_p = somme(lignes_pnl, "Réel", Exercice=an, Rubrique="Chiffre d'affaires")
    print(
        f"{an} CA ventes {ca_v:14,.2f} | CA compte de résultat {ca_p:14,.2f} | écart {ca_v - ca_p:.2f}"
    )
v26 = [l for l in lignes_ventes if l["Exercice"] == 2026 and l["Statut"] == "Réel"]
ca_r, ca_b = somme(v26, "CA Réel"), somme(v26, "CA Budget")
mb_r, mb_b = somme(v26, "Marge brute Réel"), somme(v26, "Marge brute Budget")
ec = somme(lignes_ecarts, "Montant", Exercice=2026, Type="Effet")
print(
    f"2026 cumul oct. : CA réel {ca_r:,.0f} vs budget {ca_b:,.0f} ({ca_r / ca_b - 1:+.1%})"
)
print(f"  taux de marge brute réel {mb_r / ca_r:.1%} vs budget {mb_b / ca_b:.1%}")
print(f"  écart de marge {mb_r - mb_b:,.2f} | somme des effets {ec:,.2f}")
p26 = [
    l
    for l in lignes_pnl
    if l["Exercice"] == 2026 and l["Statut"] == "Réel" and l["Ordre"] <= 7
]
print(
    f"  EBITDA réel {somme(p26, 'Réel'):,.0f} ({somme(p26, 'Réel') / ca_r:.1%}) vs budget {somme(p26, 'Budget'):,.0f} ({somme(p26, 'Budget') / ca_b:.1%})"
)
fin = [l for l in lignes_bfr if l["Date"] == date(*DERNIER_MOIS_CLOS, 1).isoformat()]
print(
    f"  créances fin oct. {somme(fin, 'Créances clients'):,.2f} | balance âgée {somme(lignes_fact, 'Montant TTC'):,.2f}"
)
print(
    f"  BFR fin oct. {somme(fin, 'BFR'):,.0f} | trésorerie fin oct. {lignes_treso[-1]['Trésorerie fin de mois']:,.0f}"
)
print(
    f"  CA réel 2026 ventes {somme(lignes_ventes, 'CA Réel', Exercice=2026):,.2f}"
    f" | agences {somme(lignes_agences, 'CA Réel', Exercice=2026):,.2f}"
)
print(
    f"  marge budget 2026 ventes {somme(lignes_ventes, 'Marge brute Budget', Exercice=2026):,.2f}"
    f" | agences {somme(lignes_agences, 'Marge brute Budget', Exercice=2026):,.2f}"
)
for l in fin:
    print(
        f"    {l['BU']:28s} DSO {l['DSO (jours)']} j (objectif {l['DSO Objectif (jours)']})"
    )
