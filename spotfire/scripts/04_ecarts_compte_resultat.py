# Onglet 4 : Écarts de marge (cascade budget -> réel) et compte de résultat analytique.
from Spotfire.Dxp.Application.Visuals import BarChart, CrossTablePlot, WaterfallChart

page = Document.Pages.AddNew("Écarts et compte de résultat")

ordre_personnalise(
    "ecarts_marge",
    "Poste",
    ["Marge brute Budget", "Effet volume & mix", "Effet prix", "Effet coûts d'achat"],
)

# 0. Soldes intermédiaires en tuiles : réel et écart au budget
SOLDES = rangee("Soldes intermédiaires")
tuiles_reel(
    SOLDES,
    [
        (
            nom,
            "M€",
            "compte_resultat",
            CLOS_2026 + " and [Ordre] <= %d" % dernier_poste,
            "Sum([Réel])",
            "Sum([Budget])",
            "Sum(Real([N-1]))",
            True,
            True,
        )
        for nom, dernier_poste in (
            ("Chiffre d'affaires", 1),
            ("Marge brute", 2),
            ("EBITDA", 7),
            ("Résultat d'exploitation", 8),
        )
    ],
)

# 1. Cascade : de la marge budget à la marge réelle
cascade = page.Visuals.AddNew[WaterfallChart]()
cascade.Data.DataTableReference = table("ecarts_marge")
cascade.Data.WhereClauseExpression = "[Exercice] = 2026"
cascade.Title = "De la marge brute budget à la marge brute réelle - cumul 2026 (k€)"
cascade.XAxis.Expression = "<[Poste]>"
cascade.YAxis.Expression = "Sum([Montant]) / 1000 as [Marge brute (k€)]"
format_axe(cascade)
cascade_coloree(cascade, "Sum([Montant])")

# 2. Effets par BU
effets = page.Visuals.AddNew[BarChart]()
effets.Data.DataTableReference = table("ecarts_marge")
effets.Data.WhereClauseExpression = '[Exercice] = 2026 and [Type] = "Effet"'
effets.Title = "Effets volume, prix et coûts d'achat par BU (k€)"
effets.XAxis.Expression = "<[BU]>"
effets.YAxis.Expression = "Sum([Montant]) / 1000 as [Effet (k€)]"
effets.ColorAxis.Expression = "<[Poste]>"
couleurs(effets.ColorAxis, COULEURS_EFFETS)
etiquettes(effets)
format_axe(effets)
legende_epuree(effets)

# 3. Compte de résultat analytique, soldes intermédiaires intercalés
# Les soldes (marge brute, EBITDA, résultat) sont des cumuls de rubriques : on les écrit
# comme des mesures, une par ligne. Pour garder Réel / Budget / Écart / N-1 en colonnes,
# ces quatre montants deviennent une dimension « Version » dans une table dépivotée.
VERSIONS = ["Réel", "Budget", "Écart", "Écart %", "Réel N-1"]


def table_des_versions():
    from Spotfire.Dxp.Data import DataColumnSignature, DataFlowBuilder, DataType
    from Spotfire.Dxp.Data.Import import DataTableDataSource
    from Spotfire.Dxp.Data.Transformations import UnpivotTransformation
    from System.Collections.Generic import List

    source = table("compte_resultat")
    for nom, expression in (
        ("Écart", "[Réel] - [Budget]"),
        ("Réel N-1", "Real([N-1])"),
        # la colonne « Écart % » n'est pas additive : elle réserve sa place parmi les
        # versions, et son calcul part du budget et de l'écart gardés sur chaque ligne
        ("Écart %", "[Budget]"),
        ("Budget base", "[Budget]"),
        ("Écart base", "[Réel] - [Budget]"),
    ):
        if not source.Columns.Contains(nom):
            source.Columns.AddCalculatedColumn(nom, expression)
    if Document.Data.Tables.Contains("resultat_lignes"):
        return

    def signatures(noms):
        liste = List[DataColumnSignature]()
        for nom in noms:
            liste.Add(DataColumnSignature(source.Columns[nom]))
        return liste

    depivot = UnpivotTransformation()
    depivot.IdentityColumns = signatures(
        ["Exercice", "Mois", "Statut", "BU", "Ordre", "Rubrique"]
        + ["Budget base", "Écart base"]
    )
    depivot.ValueColumns = signatures(VERSIONS)
    depivot.CategoryName = "Version"
    depivot.CategoryType = DataType.String
    depivot.ResultName = "Montant"
    depivot.ResultType = DataType.Real
    flux = DataFlowBuilder(DataTableDataSource(source), Application.ImportContext)
    flux.AddTransformation(depivot)
    Document.Data.Tables.Add("resultat_lignes", flux.Build())


# une ligne par rubrique, les soldes en majuscules après les rubriques qu'ils cumulent
LIGNES = [
    ("Chiffre d'affaires", "= 1"),
    ("Coût des ventes", "= 2"),
    ("MARGE BRUTE", "<= 2"),
    ("Frais de personnel", "= 3"),
    ("Marketing & commercial", "= 4"),
    ("Logistique & transport", "= 5"),
    ("Loyers & frais généraux", "= 6"),
    ("IT & systèmes", "= 7"),
    ("EBITDA", "<= 7"),
    ("Dotations aux amortissements", "= 8"),
    ("RÉSULTAT D'EXPLOITATION", "<= 8"),
]

resultat = page.Visuals.AddNew[CrossTablePlot]()
resultat.Title = "Compte de résultat analytique - cumul 2026 à fin octobre (k€)"
try:
    table_des_versions()
    ordre_personnalise("resultat_lignes", "Version", VERSIONS)
    resultat.Data.DataTableReference = table("resultat_lignes")
    resultat.Data.WhereClauseExpression = CLOS_2026
    resultat.RowAxis.Expression = "<[Axis.Default.Names]>"
    resultat.ColumnAxis.Expression = "<[Version]>"
    resultat.MeasureAxis.Expression = ", ".join(
        'If(Max([Version]) = "Écart %", '
        "Round(100 * Sum(If([Ordre] {c}, [Écart base])) "
        "/ Abs(Sum(If([Ordre] {c}, [Budget base]))), 1), "
        "Round(Sum(If([Ordre] {c}, [Montant])) / 1000, 0)) as [{l}]".format(
            c=condition, l=libelle
        )
        for libelle, condition in LIGNES
    )
    # pas de total : la dernière ligne est déjà le résultat d'exploitation
    totaux(resultat, ligne_total=False)
except Exception as erreur:
    # à défaut, le tableau simple par rubrique, sans soldes intercalés
    AVERTISSEMENTS.append("compte de résultat avec soldes : %s" % erreur)
    resultat.Data.DataTableReference = table("compte_resultat")
    resultat.Data.WhereClauseExpression = CLOS_2026
    resultat.RowAxis.Expression = "<[Ordre] NEST [Rubrique]>"
    resultat.ColumnAxis.Expression = "<[Axis.Default.Names]>"
    resultat.MeasureAxis.Expression = (
        "Integer(Round(Sum([Réel]) / 1000, 0)) as [Réel], "
        "Integer(Round(Sum([Budget]) / 1000, 0)) as [Budget], "
        "Integer(Round((Sum([Réel]) - Sum([Budget])) / 1000, 0)) as [Écart], "
        "Integer(Round(Sum(Real([N-1])) / 1000, 0)) as [N-1]"
    )
    totaux(resultat)
tableau_soigne(resultat, 85)
# montants sans décimale, écart en % avec une décimale, dans le même tableau
essayer(
    "format compte de résultat",
    lambda: setattr(resultat.Formatting, "RealFormatter", format_souple()),
)
largeur_libelles(resultat, 210)
# Spotfire ne met pas une ligne en gras : les soldes ressortent par un fond de couleur
surligner_lignes(
    resultat,
    [lib for lib, _ in LIGNES if lib == lib.upper()],
    Color.FromArgb(214, 226, 240),
)
sans_legende(resultat)

# 4. Cascade de l'écart d'EBITDA : ce que chaque rubrique ajoute ou retire au budget
RUBRIQUES = [
    "Chiffre d'affaires",
    "Coût des ventes",
    "Frais de personnel",
    "Marketing & commercial",
    "Logistique & transport",
    "Loyers & frais généraux",
    "IT & systèmes",
    "Dotations aux amortissements",
]
ordre_personnalise("compte_resultat", "Rubrique", RUBRIQUES)
charges = page.Visuals.AddNew[WaterfallChart]()
charges.Data.DataTableReference = table("compte_resultat")
charges.Data.WhereClauseExpression = CLOS_2026 + " and [Ordre] <= 7"
charges.Title = "Écart d'EBITDA vs budget - contribution de chaque rubrique (k€)"
charges.XAxis.Expression = "<[Rubrique]>"
charges.YAxis.Expression = "(Sum([Réel]) - Sum([Budget])) / 1000 as [Écart (k€)]"
format_axe(charges)
cascade_coloree(charges, "Sum([Réel]) - Sum([Budget])")

disposer(
    page,
    [
        (20, [(SOLDES, 100)]),
        (40, [(cascade, 50), (effets, 50)]),
        (40, [(resultat, 55), (charges, 45)]),
    ],
)
