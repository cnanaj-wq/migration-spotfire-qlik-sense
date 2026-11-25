# Onglet 2 : Chiffre d'affaires et marge, par produit, canal, région et mois.
from Spotfire.Dxp.Application.Visuals import (
    BarChart,
    BarChartOrientation,
    CrossTablePlot,
    LineChart,
)

page = Document.Pages.AddNew("Chiffre d'affaires et marge")

# 1. CA réel contre budget par produit
produits = page.Visuals.AddNew[BarChart]()
produits.Data.DataTableReference = table("ventes")
produits.Data.WhereClauseExpression = CLOS_2026
produits.Title = "CA par produit - réel contre budget (k€)"
produits.XAxis.Expression = "<[Produit]>"
produits.YAxis.Expression = (
    "Sum([CA Réel]) / 1000 as [Réel], Sum([CA Budget]) / 1000 as [Budget]"
)
produits.ColorAxis.Expression = "<[Axis.Default.Names]>"
essayer(
    "barres horizontales",
    lambda: setattr(produits, "Orientation", BarChartOrientation.Horizontal),
)


# réel et budget côte à côte (empilés, ils s'additionneraient à tort)
def cote_a_cote():
    from Spotfire.Dxp.Application.Visuals import StackMode

    produits.StackMode = getattr(StackMode, "None")


essayer("barres côte à côte", cote_a_cote)

couleurs(produits.ColorAxis, COULEURS_SERIES)
etiquettes(produits)
format_axe(produits)
legende_epuree(produits)

# 2. Performance des canaux : écart de CA au budget (la part de CA seule ne dit rien)
ECART_CANAL = "100 * (Sum([CA Réel]) / Sum([CA Budget]) - 1)"
canaux = page.Visuals.AddNew[BarChart]()
canaux.Data.DataTableReference = table("ventes")
canaux.Data.WhereClauseExpression = CLOS_2026
canaux.Title = "Écart de CA vs budget par canal (%)"
canaux.XAxis.Expression = "<[Canal]>"
canaux.YAxis.Expression = ECART_CANAL + " as [Écart CA (%)]"
essayer("canaux tri", lambda: setattr(canaux, "SortedBars", True))
essayer("canaux couleur", lambda: setattr(canaux.ColorAxis, "Expression", ECART_CANAL))
degrade(canaux.ColorAxis)
etiquettes(canaux)
format_axe(canaux, 1)
sans_legende(canaux)

# 3. Taux de marge brute mensuel par BU
taux = page.Visuals.AddNew[LineChart]()
taux.Data.DataTableReference = table("ventes")
taux.Data.WhereClauseExpression = CLOS_2026
taux.Title = "Taux de marge brute mensuel par BU (%)"
taux.XAxis.Expression = AXE_MOIS
taux.YAxis.Expression = (
    "100 * Sum([Marge brute Réel]) / Sum([CA Réel]) as [Taux de marge (%)]"
)
taux.ColorAxis.Expression = "<[BU]>"
couleurs(taux.ColorAxis, COULEURS_BU)
format_axe(taux, 1)
legende_epuree(taux)
legende_large(taux)

# 4. Écart de CA par région et canal
regions = page.Visuals.AddNew[CrossTablePlot]()
regions.Data.DataTableReference = table("ventes")
regions.Data.WhereClauseExpression = CLOS_2026
regions.Title = "Écart de CA vs budget par région et canal (%)"
regions.RowAxis.Expression = "<[Région]>"
regions.ColumnAxis.Expression = "<[Canal]>"
regions.MeasureAxis.Expression = (
    "Round(100 * (Sum([CA Réel]) / Sum([CA Budget]) - 1), 1) as [Écart CA (%)]"
)
totaux(regions)
tableau_soigne(regions, 120)
carte_de_chaleur(regions)
largeur_libelles(regions, 120)
sans_legende(regions)

# 5. Indicateurs clés par BU (montants en milliers d'euros, taux en %)
indicateurs = page.Visuals.AddNew[CrossTablePlot]()
indicateurs.Data.DataTableReference = table("ventes")
indicateurs.Data.WhereClauseExpression = CLOS_2026
indicateurs.Title = "Indicateurs clés par BU - cumul 2026 à fin octobre (k€)"
indicateurs.RowAxis.Expression = "<[BU]>"
indicateurs.ColumnAxis.Expression = "<[Axis.Default.Names]>"
indicateurs.MeasureAxis.Expression = (
    "Integer(Round(Sum([CA Réel]) / 1000, 0)) as [CA réel], "
    "Integer(Round(Sum([CA Budget]) / 1000, 0)) as [CA budget], "
    "Round(100 * (Sum([CA Réel]) / Sum([CA Budget]) - 1), 1) as [% vs budget], "
    "Integer(Round(Sum(Real([CA N-1])) / 1000, 0)) as [CA N-1], "
    "Round(100 * (Sum([CA Réel]) / Sum(Real([CA N-1])) - 1), 1) as [% vs N-1], "
    "Integer(Round(Sum([Marge brute Réel]) / 1000, 0)) as [Marge réelle], "
    "Round(100 * Sum([Marge brute Réel]) / Sum([CA Réel]), 1) as [Taux réel %], "
    "Round(100 * Sum([Marge brute Budget]) / Sum([CA Budget]), 1) as [Taux budget %], "
    "Integer(Round((Sum([Marge brute Réel]) - Sum([Marge brute Budget])) / 1000, 0)) "
    "as [Écart marge]"
)
totaux(indicateurs)
tableau_soigne(indicateurs, 105)
largeur_libelles(indicateurs, 190)
sans_legende(indicateurs)

disposer(
    page,
    [
        (38, [(produits, 60), (canaux, 40)]),
        (22, [(indicateurs, 100)]),
        (40, [(taux, 55), (regions, 45)]),
    ],
)
