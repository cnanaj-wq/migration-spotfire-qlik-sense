# Onglet 1 : Synthèse direction. Cumul 2026 sur les mois clôturés, réel contre budget et N-1.
# Exécuté par construire_tout.py (qui fournit table, disposer, la charte et CLOS_2026).
from Spotfire.Dxp.Application.Visuals import (
    BarChart,
    CombinationChart,
    KpiChart,
    LineChart,
)

page = Document.Pages.AddNew("Synthèse direction")


# 0. Tuiles : l'indicateur en grand, son écart en dessous, couleur selon l'écart
# (vert favorable, ambre à surveiller, rouge critique).
def rangee(titre):
    visuel = page.Visuals.AddNew[KpiChart]()
    visuel.Title = titre
    # le libellé de chaque tuile suffit : sans bandeau de titre, la rangée gagne en hauteur
    essayer("titre rangée", lambda: setattr(visuel.Visual, "ShowTitle", False))

    def police():
        actuelle = visuel.BaseFontMetadata
        visuel.BaseFontMetadata = actuelle.WithSize(actuelle.Size * 1.2, actuelle.Unit)

    essayer("police tuiles", police)
    # pas de bandeau au-dessus des tuiles : le contenu remonte et la référence respire
    essayer("bandeau tuiles", lambda: setattr(visuel, "ShowTitlesForKpis", False))
    return visuel


RANGEE_REEL = rangee("Réel et écart au budget")
RANGEE_N1 = rangee("Écart à N-1")


def tuile(
    tuiles,
    titre,
    nom_table,
    filtre,
    valeur,
    reference,
    ecart_favorable,
    unite,
    signe=None,
    signe_reference=None,
    unite_reference=None,
    axe_temps=True,
    couleur=None,
):
    """ecart_favorable : écart en %, positif quand le réel est meilleur que la référence.

    signe : la valeur est un écart signé (« % » ou « pts ») ; signe_reference : idem
    pour le chiffre du bas. unite_reference : unité du chiffre du bas si elle diffère.
    axe_temps=False : indicateur sans historique mensuel. couleur : fond fixe.
    """
    contenu = tuiles.KpiCollection.AddNew()
    kpi = contenu.Visualization
    kpi.Data.DataTableReference = table(nom_table)
    kpi.Data.WhereClauseExpression = filtre
    kpi.Title = titre
    essayer("titre tuile " + titre, lambda: setattr(contenu, "Title", titre))
    kpi.YAxis.Expression = valeur
    essayer(
        "référence " + titre,
        lambda: setattr(kpi.ComparativeAxis, "Expression", reference),
    )
    essayer("tuile unique " + titre, lambda: setattr(kpi.TileAxis, "Expression", "<>"))
    # axe mensuel : la tuile affiche la valeur du dernier mois clos et, à droite,
    # la courbe de janvier à ce mois (l'espace ne reste pas vide)
    if axe_temps:
        essayer(
            "axe temps " + titre, lambda: setattr(kpi.XAxis, "Expression", "<[Mois]>")
        )
    essayer("courbe " + titre, lambda: setattr(kpi, "ShowSparkline", True))
    essayer(
        "échelle courbe " + titre, lambda: setattr(kpi, "ShowSparklineScale", False)
    )
    if couleur is not None:
        essayer(
            "couleur fixe " + titre,
            lambda: setattr(kpi.ColorAxis.Coloring, "DefaultColor", couleur),
        )
    else:
        essayer(
            "couleur " + titre,
            lambda: setattr(kpi.ColorAxis, "Expression", ecart_favorable),
        )
        degrade(kpi.ColorAxis, tranche=True)
    essayer(
        "format " + titre,
        lambda: setattr(
            kpi.YAxis.Formatting,
            "RealFormatter",
            format_ecart(signe) if signe else format_unite(unite),
        ),
    )
    # même précision pour la référence que pour la valeur
    essayer(
        "format référence " + titre,
        lambda: setattr(
            kpi.ComparativeAxis.Formatting,
            "RealFormatter",
            format_ecart(signe_reference)
            if signe_reference
            else format_unite(unite_reference or unite),
        ),
    )


# Chaque indicateur se lit sur deux tuiles : le réel avec son écart au budget,
# puis l'écart à N-1.
INDICATEURS = [
    # titre court, unité, table, filtre, réel, budget, N-1, hausse favorable ?, cumul ?
    # cumul = True : la valeur est le cumul depuis janvier ; False : la valeur du mois
    (
        "CA",
        "M€",
        "ventes",
        CLOS_2026,
        "Sum([CA Réel])",
        "Sum([CA Budget])",
        "Sum(Real([CA N-1]))",
        True,
        True,
    ),
    (
        "Marge brute",
        "M€",
        "ventes",
        CLOS_2026,
        "Sum([Marge brute Réel])",
        "Sum([Marge brute Budget])",
        "Sum(Real([Marge brute N-1]))",
        True,
        True,
    ),
    (
        "Taux de marge",
        "%",
        "ventes",
        CLOS_2026,
        "100 * Sum([Marge brute Réel]) / Sum([CA Réel])",
        "100 * Sum([Marge brute Budget]) / Sum([CA Budget])",
        "100 * Sum(Real([Marge brute N-1])) / Sum(Real([CA N-1]))",
        True,
        True,
    ),
    (
        "EBITDA",
        "M€",
        "compte_resultat",
        CLOS_2026 + " and [Ordre] <= 7",
        "Sum([Réel])",
        "Sum([Budget])",
        "Sum(Real([N-1]))",
        True,
        True,
    ),
    (
        "BFR fin de mois",
        "M€",
        "bfr",
        "[Mois] <= %d and [Exercice] >= 2025" % DERNIER_MOIS,
        "Sum(If([Exercice] = 2026, [BFR]))",
        "Sum(If([Exercice] = 2026, [BFR Objectif]))",
        "Sum(If([Exercice] = 2025, [BFR]))",
        False,
        False,
    ),
]


def cumule(expression):
    """Transforme chaque Sum(...) en cumul depuis janvier le long de l'axe des mois."""
    resultat, i = "", 0
    while i < len(expression):
        if expression.startswith("Sum(", i):
            niveau, j = 0, i + 3
            while True:
                niveau += {"(": 1, ")": -1}.get(expression[j], 0)
                j += 1
                if niveau == 0:
                    break
            resultat += expression[i:j] + " OVER (AllPrevious([Axis.X]))"
            i = j
        else:
            resultat += expression[i]
            i += 1
    return resultat


def preparer(indicateur):
    nom, unite, source, filtre, reel, budget, n1, hausse, cumul = indicateur
    if cumul:
        reel, budget, n1 = cumule(reel), cumule(budget), cumule(n1)
    # libellés sans période : ils restent justes quand on sélectionne un mois
    court = nom.replace(" fin de mois", "")
    cible = "budget" if cumul else "objectif"
    libelles = {
        "reel": "%s réel 2026" % court,
        "vs_budget": "vs %s 2026" % cible,
        "vs_n1": "%s vs 2025" % court,
        "budget": "%s 2026" % cible.capitalize(),
        "n1": "Réel 2025",
    }
    return nom, unite, source, filtre, reel, budget, n1, hausse, libelles


def en_unite(expression, unite):
    """Montants en millions d'euros ; taux (%) et délais (j) tels quels."""
    return expression if unite in ("%", "j") else "(" + expression + ") / 1000000"


def ecart(reel, reference, unite):
    """Écart en % pour un montant, en points pour un taux."""
    if unite == "%":
        return "(" + reel + ") - (" + reference + ")"
    return "100 * ((" + reel + ") / (" + reference + ") - 1)"


def favorable(reel, reference, hausse):
    """Écart en %, positif quand il est favorable (sert à la couleur de la tuile)."""
    meilleur, repere = (reel, reference) if hausse else (reference, reel)
    return "100 * ((%s) / (%s) - 1)" % (meilleur, repere)


def tuiles_reel(tuiles, indicateurs):
    """Une tuile par indicateur : le réel en grand, l'écart au budget en dessous."""
    for nom, unite, source, filtre, reel, budget, n1, hausse, lib in map(
        preparer, indicateurs
    ):
        tuile(
            tuiles,
            "%s (%s)" % (nom, unite),
            source,
            filtre,
            en_unite(reel, unite) + " as [%s]" % lib["reel"],
            ecart(reel, budget, unite) + " as [%s]" % lib["vs_budget"],
            favorable(reel, budget, hausse),
            unite,
            signe_reference="pts" if unite == "%" else "%",
        )


def tuiles_n1(tuiles, indicateurs):
    """Une tuile par indicateur : l'écart à N-1 en grand, le réel N-1 en dessous."""
    for nom, unite, source, filtre, reel, budget, n1, hausse, lib in map(
        preparer, indicateurs
    ):
        tuile(
            tuiles,
            "%s vs N-1" % nom,
            source,
            filtre,
            ecart(reel, n1, unite) + " as [%s]" % lib["vs_n1"],
            en_unite(n1, unite) + " as [%s]" % lib["n1"],
            favorable(reel, n1, hausse),
            unite,
            signe="pts" if unite == "%" else "%",
        )


tuiles_reel(RANGEE_REEL, INDICATEURS)
tuiles_n1(RANGEE_N1, INDICATEURS)

# 2. CA mensuel : réel, budget, N-1
mensuel = page.Visuals.AddNew[LineChart]()
mensuel.Data.DataTableReference = table("ventes")
mensuel.Data.WhereClauseExpression = "[Exercice] = 2026"
mensuel.Title = "Chiffre d'affaires mensuel 2026 - réel, budget, N-1 (k€)"
mensuel.XAxis.Expression = AXE_MOIS
mensuel.YAxis.Expression = (
    "Sum([CA Réel]) / 1000 as [Réel], Sum([CA Budget]) / 1000 as [Budget], "
    "Sum(Real([CA N-1])) / 1000 as [N-1]"
)
mensuel.ColorAxis.Expression = "<[Axis.Default.Names]>"
couleurs(mensuel.ColorAxis, COULEURS_SERIES)
format_axe(mensuel)
legende_epuree(mensuel)

# 3. Écart de marge brute par BU
ecart_bu = page.Visuals.AddNew[BarChart]()
ecart_bu.Data.DataTableReference = table("ventes")
ecart_bu.Data.WhereClauseExpression = CLOS_2026
ecart_bu.Title = "Écart de marge brute vs budget par BU (k€)"
ecart_bu.XAxis.Expression = "<[BU]>"
ECART_MARGE = "(Sum([Marge brute Réel]) - Sum([Marge brute Budget])) / 1000"
ecart_bu.YAxis.Expression = ECART_MARGE + " as [Écart de marge]"
essayer(
    "couleur écart BU", lambda: setattr(ecart_bu.ColorAxis, "Expression", ECART_MARGE)
)
degrade(ecart_bu.ColorAxis)
etiquettes(ecart_bu)
format_axe(ecart_bu)
sans_legende(ecart_bu)

# 4. EBITDA mensuel réel contre budget (rubriques 1 à 7 du compte de résultat)
ebitda = page.Visuals.AddNew[CombinationChart]()
ebitda.Data.DataTableReference = table("compte_resultat")
ebitda.Data.WhereClauseExpression = CLOS_2026 + " and [Ordre] <= 7"
ebitda.Title = "EBITDA mensuel 2026 - réel contre budget (k€)"
ebitda.XAxis.Expression = AXE_MOIS
ebitda.YAxis.Expression = (
    "Sum([Réel]) / 1000 as [Réel], Sum([Budget]) / 1000 as [Budget]"
)
ebitda.ColorAxis.Expression = "<[Axis.Default.Names]>"
couleurs(ebitda.ColorAxis, COULEURS_SERIES)
format_axe(ebitda)
legende_epuree(ebitda)

disposer(
    page,
    [
        (24, [(RANGEE_REEL, 100)]),
        (21, [(RANGEE_N1, 100)]),
        (55, [(mensuel, 40), (ecart_bu, 25), (ebitda, 35)]),
    ],
)
