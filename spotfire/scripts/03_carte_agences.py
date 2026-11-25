# Onglet 3 : Carte des 24 agences. Taille = CA réel, couleur = écart au budget.
from Spotfire.Dxp.Application.Visuals import (
    BarChart,
    BarChartOrientation,
    CrossTablePlot,
)
from Spotfire.Dxp.Application.Visuals.Maps import MapChart, MarkerLayerVisualization

page = Document.Pages.AddNew("Carte des agences")
ECART_CA = "100 * (Sum([CA Réel]) / Sum([CA Budget]) - 1)"
# en valeur : une grosse agence à -2 % pèse plus qu'une petite à -4 %
ECART_CA_KE = "(Sum([CA Réel]) - Sum([CA Budget])) / 1000"

# 1. Carte
carte = page.Visuals.AddNew[MapChart]()
carte.Title = "Agences - taille : CA réel 2026, couleur : écart au budget (%)"
couche = None
for c in carte.Layers:
    if isinstance(c, MarkerLayerVisualization):
        couche = c
if couche is None:
    retour = carte.Layers.AddNewMarkerLayer(table("ventes_agences"))
    # selon la version, Spotfire renvoie la couche seule ou un tuple qui la contient
    for element in retour if isinstance(retour, tuple) else (retour,):
        if isinstance(element, MarkerLayerVisualization):
            couche = element
couche.Data.DataTableReference = table("ventes_agences")
couche.Data.WhereClauseExpression = CLOS_2026
essayer("carte longitude", lambda: setattr(couche.XAxis, "Expression", "[Longitude]"))
essayer("carte latitude", lambda: setattr(couche.YAxis, "Expression", "[Latitude]"))
essayer(
    "carte marqueur", lambda: setattr(couche.MarkerByAxis, "Expression", "<[Agence]>")
)
essayer(
    "carte taille", lambda: setattr(couche.SizeAxis, "Expression", "Sum([CA Réel])")
)
essayer("carte couleur", lambda: setattr(couche.ColorAxis, "Expression", ECART_CA))


# fond de carte (tuiles standard) placé sous les marqueurs
def fond_de_carte():
    carte.Layers.AddNewStandardTileLayer()


essayer("carte fond", fond_de_carte)


# marqueurs ronds, étiquetés, du rouge (sous le budget) au vert (au-dessus)
def habiller_marqueurs():
    from Spotfire.Dxp.Application.Visuals import MarkerShape, MarkerType

    couche.ShapeAxis.DefaultShape = MarkerShape(MarkerType.Circle)


# la couche de tuiles vient d'être ajoutée au-dessus : on la passe sous les marqueurs
essayer("carte ordre des couches", lambda: carte.Layers.Move(1, 0))
essayer("carte forme", habiller_marqueurs)
degrade(couche.ColorAxis)
essayer("carte taille des marqueurs", lambda: setattr(couche, "MarkerSize", 12.0))
legende_epuree(carte)
essayer("carte cadrage", lambda: setattr(carte, "AutoZoom", True))


# 2. Classement des agences par écart de CA
classement = page.Visuals.AddNew[BarChart]()
classement.Data.DataTableReference = table("ventes_agences")
classement.Data.WhereClauseExpression = CLOS_2026
classement.Title = "Écart de CA vs budget par agence (k€)"
classement.XAxis.Expression = "<[Agence]>"
classement.YAxis.Expression = ECART_CA_KE + " as [Écart CA (k€)]"
essayer("classement tri", lambda: setattr(classement, "SortedBars", True))
essayer(
    "classement horizontal",
    lambda: setattr(classement, "Orientation", BarChartOrientation.Horizontal),
)
essayer(
    "classement couleur",
    lambda: setattr(classement.ColorAxis, "Expression", ECART_CA_KE),
)
degrade(classement.ColorAxis)
etiquettes(classement)
format_axe(classement)
police_axe(classement, 0.8)
sans_legende(classement)

# 3. Détail par région et agence
detail = page.Visuals.AddNew[CrossTablePlot]()
detail.Data.DataTableReference = table("ventes_agences")
detail.Data.WhereClauseExpression = CLOS_2026
detail.Title = "Détail par région et agence (k€)"
detail.RowAxis.Expression = "<[Région] NEST [Agence]>"
detail.ColumnAxis.Expression = "<[Axis.Default.Names]>"
detail.MeasureAxis.Expression = (
    "Integer(Round(Sum([CA Réel]) / 1000, 0)) as [CA réel], "
    "Integer(Round(Sum([CA Budget]) / 1000, 0)) as [CA budget], "
    "Integer(Round(" + ECART_CA_KE + ", 0)) as [Écart k€], "
    "Round(" + ECART_CA + ", 1) as [Écart %], "
    "Round(100 * Sum([Marge brute Réel]) / Sum([CA Réel]), 1) as [Taux marge %]"
)
totaux(detail)
tableau_soigne(detail, 75)
largeur_libelles(detail, 110)
sans_legende(detail)

disposer(page, [(100, [(carte, 36), (classement, 30), (detail, 34)])])
