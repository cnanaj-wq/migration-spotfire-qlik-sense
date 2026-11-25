# Script IronPython Spotfire - test : verifie que l'essai autorise les scripts.
# Renomme la table des agences et cree une page avec un histogramme.
from Spotfire.Dxp.Application.Visuals import BarChart

for table in Document.Data.Tables:
    if table.Name.endswith("ventes_agences"):
        table.Name = "ventes_agences"

page = Document.Pages.AddNew("Test script")
graphe = page.Visuals.AddNew[BarChart]()
graphe.Data.DataTableReference = Document.Data.Tables["ventes"]
graphe.XAxis.Expression = "<[BU]>"
graphe.YAxis.Expression = "Sum([CA Réel])"
graphe.Title = "CA réel par BU"
Document.ActivePageReference = page
