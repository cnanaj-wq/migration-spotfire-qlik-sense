"""Étape 1 : lit le fichier Spotfire (.dxp) et en sort l'inventaire des pages et des visuels.

Usage : python lab02/extraire.py
Un fichier .dxp est une archive ZIP ; son document, AnalysisDocument.xml, décrit chaque objet
Spotfire avec son type et ses propriétés. Le script le parcourt sans ouvrir Spotfire.
Résultat : lab02/sorties/inventaire.json
"""

import json
import pathlib
import xml.etree.ElementTree as ET
import zipfile

RACINE = pathlib.Path(__file__).parent.parent
DXP = RACINE / "spotfire" / "controle_gestion_orvane.dxp"
SORTIES = pathlib.Path(__file__).parent / "sorties"
NS = "{http://www.spotfire.com/schemas/Document1.0.xsd}"
VISUELS = "Spotfire.Dxp.Application.Visuals."
IGNORES = {
    "Data",
    "Legend",
    "TitleExpression",
    "DescriptionExpression",
    "KpiCollection",
}


class Document:
    """Le graphe d'objets du document : types, objets et renvois entre objets."""

    def __init__(self, chemin):
        with zipfile.ZipFile(chemin) as archive:
            self.racine = ET.fromstring(archive.read("AnalysisDocument.xml"))
        self.types = {
            t.get("Id"): t.get("FullTypeName")
            for t in self.racine.iter(NS + "TypeObject")
        }
        self.par_id = {e.get("Id"): e for e in self.racine.iter() if e.get("Id")}

    def suivre(self, element):
        """L'élément lui-même, ou celui qu'il désigne si c'est un renvoi."""
        if element is not None and element.tag == NS + "ObjectRef":
            return self.par_id.get(element.get("Value"))
        return element

    def type(self, element):
        marque = element.find(NS + "Type") if element is not None else None
        if marque is None or not len(marque):
            return ""
        return self.types.get(marque[0].get("Id") or marque[0].get("Value"), "")

    def champs(self, element):
        bloc = element.find(NS + "Fields") if element is not None else None
        if bloc is None:
            return {}
        trouves = {c.get("Name"): self.suivre(c[0]) for c in bloc if len(c)}
        return {nom: valeur for nom, valeur in trouves.items() if valeur is not None}

    def champ(self, element, *chemin):
        for nom in chemin:
            element = self.champs(element).get(nom)
            if element is None:
                return None
        return element

    def texte(self, element, *chemin):
        cible = self.champ(element, *chemin)
        return cible.get("Value", "") if cible is not None else ""

    def elements(self, tableau):
        """Les éléments d'une collection, qu'elle soit un tableau ou un objet qui en porte un."""
        if tableau is None:
            return []
        if tableau.tag != NS + "Array":
            interne = self.champs(tableau)
            tableau = next(
                (interne[n] for n in ("Items", "_items", "items") if n in interne), None
            )
            return self.elements(tableau)
        bloc = tableau.find(NS + "Elements")
        return [self.suivre(e) for e in bloc] if bloc is not None else []

    def expressions(self, element, chemin="", vus=None):
        """Toutes les expressions non vides portées par un objet et ses sous-objets."""
        vus = set() if vus is None else vus
        trouvees = {}
        if element is None or element.get("Id") in vus:
            return trouvees
        vus.add(element.get("Id"))
        bloc = element.find(NS + "Fields")
        for champ in bloc if bloc is not None else []:
            nom, valeur = champ.get("Name"), champ[0] if len(champ) else None
            if valeur is None or nom in IGNORES:
                continue
            ici = (chemin + "." + nom).strip(".")
            if nom == "Expression":
                valeur = self.suivre(valeur)
                if valeur is not None and valeur.get("Value") not in (None, "", "<>"):
                    trouvees[chemin.replace(".ExpressionTexts", "")] = valeur.get(
                        "Value"
                    )
            elif valeur.tag == NS + "Object":
                # on ne suit pas les renvois : ils mènent hors du visuel
                trouvees.update(self.expressions(valeur, ici, vus))
            elif valeur.tag == NS + "Array":
                for rang, objet in enumerate(valeur.iter(NS + "Object")):
                    trouvees.update(
                        self.expressions(objet, "%s[%d]" % (ici, rang), vus)
                    )
        return trouvees


def decrire(doc, contenu):
    """Type, table, limitation et expressions d'un visuel."""
    donnees = doc.champ(contenu, "Data")
    return {
        "type": doc.type(contenu).replace(VISUELS, ""),
        "table": doc.texte(donnees, "DataTable", "Name"),
        "limitation": doc.texte(
            donnees, "WhereClauseExpression", "PreProcessedExpression"
        ),
        "expressions": doc.expressions(contenu),
    }


def inventaire(doc):
    pages = []
    for page in (
        o for o in doc.racine.iter(NS + "Object") if doc.type(o).endswith(".Page")
    ):
        visuels = []
        for visuel in doc.elements(doc.champ(page, "Visuals")):
            contenu = doc.champ(visuel, "InternalContent")
            fiche = {"titre": doc.texte(visuel, "TitleExpression", "Expression")}
            fiche.update(decrire(doc, contenu))
            cartes = doc.elements(doc.champ(contenu, "KpiCollection"))
            if cartes:
                fiche["indicateurs"] = [
                    dict(
                        titre=doc.texte(c, "TitleExpression", "Expression"),
                        **decrire(doc, doc.champ(c, "MiniatureVisualization")),
                    )
                    for c in cartes
                ]
            visuels.append(fiche)
        pages.append(
            {
                "titre": doc.texte(page, "TitleExpression", "Expression"),
                "visuels": visuels,
            }
        )
    return pages


def main():
    doc = Document(DXP)
    tables = sorted(
        {
            doc.texte(o, "Name")
            for o in doc.racine.iter(NS + "Object")
            if doc.type(o).endswith("Data.DataTable")
        }
    )
    pages = inventaire(doc)
    SORTIES.mkdir(exist_ok=True)
    (SORTIES / "inventaire.json").write_text(
        json.dumps({"tables": tables, "pages": pages}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    for page in pages:
        print("%-36s %d visuels" % (page["titre"], len(page["visuels"])))
    print("%d tables, %d pages" % (len(tables), len(pages)))


if __name__ == "__main__":
    main()
