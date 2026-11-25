# Onglet 5 : BFR, trésorerie et balance âgée des créances clients.
from Spotfire.Dxp.Application.Visuals import (
    BarChart,
    BarChartOrientation,
    CombinationChart,
    LineChart,
)

page = Document.Pages.AddNew("BFR, trésorerie et balance âgée")

ordre_personnalise(
    "creances_clients",
    "Tranche",
    ["Non échu", "1 à 30 jours", "31 à 60 jours", "61 à 90 jours", "Plus de 90 jours"],
)

# 0. Bandeau cash : le dernier mois clos contre son objectif
CASH = rangee("Pilotage du cash")
FIN_DE_MOIS = "[Mois] <= %d and [Exercice] >= 2025" % DERNIER_MOIS


def delai(nom, colonne, hausse):
    """Délai moyen des BU (jours) : réel 2026 contre objectif."""
    return (
        nom + " fin de mois",
        "j",
        "bfr",
        FIN_DE_MOIS,
        "Avg(If([Exercice] = 2026, [%s (jours)]))" % colonne,
        "Avg(If([Exercice] = 2026, [%s Objectif (jours)]))" % colonne,
        "Avg(If([Exercice] = 2025, [%s (jours)]))" % colonne,
        hausse,
        False,
    )


def cycle(suffixe, exercice):
    """Cycle de conversion de trésorerie : DSO + DIO - DPO (moyennes des BU)."""
    return " ".join(
        "%s Avg(If([Exercice] = %d, [%s%s (jours)]))" % (signe, exercice, nom, suffixe)
        for signe, nom in (("", "DSO"), ("+", "DIO"), ("-", "DPO"))
    )


CYCLE = (
    "Cycle de conversion fin de mois",
    "j",
    "bfr",
    FIN_DE_MOIS,
    cycle("", 2026),
    cycle(" Objectif", 2026),
    cycle("", 2025),
    False,
    False,
)

tuiles_reel(
    CASH,
    [
        INDICATEURS[4],
        delai("DSO moyen", "DSO", False),
        delai("DIO moyen", "DIO", False),
        # payer plus tard ses fournisseurs soulage le BFR : la hausse est favorable
        delai("DPO moyen", "DPO", True),
        CYCLE,
    ],
)

# trésorerie de fin de mois, comparée au même mois de l'exercice précédent
TRESO_2026 = "Sum(If([Exercice] = 2026, [Trésorerie fin de mois]))"
TRESO_2025 = "Sum(If([Exercice] = 2025, [Trésorerie fin de mois]))"
tuile(
    CASH,
    "Trésorerie",
    "tresorerie",
    FIN_DE_MOIS,
    en_unite(TRESO_2026, "M€") + " as [Trésorerie disponible 2026]",
    ecart(TRESO_2026, TRESO_2025, "M€") + " as [vs 2025]",
    favorable(TRESO_2026, TRESO_2025, True),
    "M€",
    signe_reference="%",
)

# créances échues depuis plus de 90 jours : une photo au 31/10, sans historique mensuel.
# Le bandeau porte six tuiles au plus sur une ligne : celle-ci se place à gauche de
# la balance âgée, dont elle résume la dernière tranche.
RISQUE = rangee("Risque client")
PLUS_DE_90 = 'Sum(If([Tranche] = "Plus de 90 jours", [Montant TTC]))'
tuile(
    RISQUE,
    "Créances à plus de 90 jours",
    "creances_clients",
    "",
    en_unite(PLUS_DE_90, "M€") + " as [Créances à plus de 90 jours]",
    "100 * %s / Sum([Montant TTC]) as [de l'encours clients]" % PLUS_DE_90,
    "0",
    "M€",
    unite_reference="%",
    axe_temps=False,
    couleur=BLEU_NUIT,
)

# 1. DSO par BU, mois par mois
dso = page.Visuals.AddNew[LineChart]()
dso.Data.DataTableReference = table("bfr")
dso.Data.WhereClauseExpression = "[Exercice] = 2026"
dso.Title = "DSO 2026 par BU (jours)"
dso.XAxis.Expression = AXE_MOIS
dso.YAxis.Expression = "Avg([DSO (jours)]) as [DSO]"
dso.ColorAxis.Expression = "<[BU]>"
couleurs(dso.ColorAxis, COULEURS_BU)
format_axe(dso)
legende_epuree(dso)
legende_large(dso)

# 2. BFR contre objectif
bfr = page.Visuals.AddNew[CombinationChart]()
bfr.Data.DataTableReference = table("bfr")
bfr.Data.WhereClauseExpression = "[Exercice] = 2026"
bfr.Title = "BFR 2026 - réel contre objectif (k€)"
bfr.XAxis.Expression = AXE_MOIS
bfr.YAxis.Expression = (
    "Sum([BFR]) / 1000 as [Réel], Sum([BFR Objectif]) / 1000 as [Objectif]"
)
bfr.ColorAxis.Expression = "<[Axis.Default.Names]>"
couleurs(bfr.ColorAxis, COULEURS_SERIES)
format_axe(bfr)
legende_epuree(bfr)

# 3. Trésorerie de fin de mois sur trois exercices
tresorerie = page.Visuals.AddNew[LineChart]()
tresorerie.Data.DataTableReference = table("tresorerie")
tresorerie.Title = "Trésorerie de fin de mois (k€)"
tresorerie.XAxis.Expression = "<[Exercice] NEST [Période]>"
tresorerie.YAxis.Expression = "Sum([Trésorerie fin de mois]) / 1000 as [Trésorerie]"
couleur_unique(tresorerie, BLEU_NUIT)
format_axe(tresorerie)
sans_legende(tresorerie)

# 4. Balance âgée par tranche de retard
balance = page.Visuals.AddNew[BarChart]()
balance.Data.DataTableReference = table("creances_clients")
balance.Title = "Balance âgée au 31/10/2026 par tranche de retard (k€)"
balance.XAxis.Expression = "<[Tranche]>"
balance.YAxis.Expression = "Sum([Montant TTC]) / 1000 as [Montant TTC (k€)]"
balance.ColorAxis.Expression = "<[BU]>"
couleurs(balance.ColorAxis, COULEURS_BU)
etiquettes(balance)
format_axe(balance)
legende_epuree(balance)
legende_large(balance)

# 5. Créances échues : les plus gros montants d'abord
clients = page.Visuals.AddNew[BarChart]()
clients.Data.DataTableReference = table("creances_clients")
clients.Data.WhereClauseExpression = '[Échu] = "Échu"'
clients.Title = "Créances échues - les 15 clients les plus exposés (k€)"
# on ne garde que les 15 plus gros encours échus : 60 barres ne se lisent pas
TOP_15 = (
    '[Échu] = "Échu" and DenseRank(Sum(If([Échu] = "Échu", [Montant TTC], 0)) '
    'OVER ([Client]), "desc") <= 15'
)
essayer(
    "clients top 15",
    lambda: setattr(clients.Data, "WhereClauseExpression", TOP_15),
)
clients.XAxis.Expression = "<[Client]>"
clients.YAxis.Expression = "Sum([Montant TTC]) / 1000 as [Montant échu (k€)]"
essayer("clients tri", lambda: setattr(clients, "SortedBars", True))
essayer(
    "clients horizontal",
    lambda: setattr(clients, "Orientation", BarChartOrientation.Horizontal),
)
# le client le plus exposé en haut du graphique
essayer("clients ordre", lambda: setattr(clients.XAxis, "Reversed", True))
couleur_unique(clients, BLEU_NUIT)
format_axe(clients)
sans_legende(clients)


def libelles_a_plat():
    from Spotfire.Dxp.Application.Visuals import LabelOrientation

    clients.XAxis.Scale.LabelOrientation = LabelOrientation.Horizontal


essayer("clients libellés", libelles_a_plat)

disposer(
    page,
    [
        (20, [(CASH, 100)]),
        (40, [(dso, 34), (bfr, 33), (tresorerie, 33)]),
        (40, [(RISQUE, 16), (balance, 42), (clients, 42)]),
    ],
)
