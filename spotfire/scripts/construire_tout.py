# Script IronPython Spotfire - construit les cinq onglets du tableau de bord.
# Lancé depuis Spotfire par le script « lancer_script_du_depot ».
# Relançable : les nouveaux onglets sont créés, puis les anciens sont supprimés.
import io
import re

from Spotfire.Dxp.Application.Layout import LayoutDefinition
from System.Drawing import Color
from System.IO import Path

# les scripts sont lus dans le dossier « scripts » placé à côté du document Spotfire :
# le dépôt peut être cloné n'importe où. Le premier nom est renseigné quand le document
# vient d'être ouvert, le second quand il a été enregistré sous un nouveau nom.
_DOCUMENT = (
    Application.DocumentMetadata.LoadedFromFileName
    or Application.DocumentMetadata.FileNameUsedBySave
)
DOSSIER = Path.GetDirectoryName(_DOCUMENT) + "/scripts/"
ONGLETS = [
    "01_synthese_direction.py",
    "02_chiffre_affaires_marge.py",
    "03_carte_agences.py",
    "04_ecarts_compte_resultat.py",
    "05_bfr_tresorerie.py",
]
CLOS_2026 = '[Exercice] = 2026 and [Statut] = "Réel"'
AVERTISSEMENTS = []

# Charte : une couleur par notion, la même sur tous les onglets.
BLEU_NUIT = Color.FromArgb(31, 58, 95)
GRIS = Color.FromArgb(167, 177, 189)
AMBRE = Color.FromArgb(224, 164, 88)
VERT = Color.FromArgb(34, 139, 94)
ROUGE = Color.FromArgb(214, 69, 65)
NEUTRE = Color.FromArgb(240, 236, 226)
# écart défavorable (en %) au-delà duquel une tuile passe de l'ambre au rouge
SEUIL_ALERTE = 5.0
COULEURS_SERIES = {
    "Réel": BLEU_NUIT,
    "Budget": GRIS,
    "N-1": AMBRE,
    "Objectif": GRIS,
}
COULEURS_BU = {
    "Chauffage & Climatisation": BLEU_NUIT,
    "Électricité": Color.FromArgb(42, 157, 143),
    "Outillage": Color.FromArgb(233, 196, 106),
    "Services": Color.FromArgb(231, 111, 81),
}
COULEURS_CANAL = {
    "Agences": BLEU_NUIT,
    "Grands comptes": Color.FromArgb(42, 157, 143),
    "E-commerce": Color.FromArgb(233, 196, 106),
}
COULEURS_EFFETS = {
    "Effet volume & mix": BLEU_NUIT,
    "Effet prix": Color.FromArgb(42, 157, 143),
    "Effet coûts d'achat": Color.FromArgb(231, 111, 81),
}
# entrées de légende sans intérêt pour le lecteur (libellés français et anglais)
LEGENDE_INUTILE = (
    "Limitation de données",
    "Data limiting",
    "Marquage",
    "Marking",
    "Aligner par",
    "Line by",
    "Forme par",
    "Shape by",
    "Marquer par",
    "Marker by",
    "Couche de marqueurs",
)


def essayer(libelle, action):
    """Réglage facultatif : en cas d'échec on le note et on continue."""
    try:
        action()
    except Exception as erreur:
        AVERTISSEMENTS.append("%s : %s" % (libelle, erreur))


def table(nom):
    return Document.Data.Tables[nom]


def sans_legende(visuel):
    essayer("légende " + visuel.Title, lambda: setattr(visuel.Legend, "Visible", False))


def legende_epuree(visuel):
    """Ne garde dans la légende que ce qui aide à lire le graphique."""

    def epurer():
        for element in visuel.Legend.Items:
            if element.Title in LEGENDE_INUTILE:
                element.Visible = False

    essayer("légende épurée " + visuel.Title, epurer)


def couleurs(axe, palette):
    """Couleur fixe par catégorie (BU, série réel/budget, canal...)."""
    from Spotfire.Dxp.Application.Visuals import CategoryKey

    for categorie, couleur in palette.items():
        essayer(
            "couleur " + categorie,
            lambda c=categorie, k=couleur: axe.Coloring.SetColorForCategory(
                CategoryKey(c), k
            ),
        )


def degrade(axe, tranche=False, binaire=False):
    """Du rouge (défavorable) au vert (favorable), neutre à zéro.

    tranche=True : trois niveaux pour les tuiles, sur un écart en % déjà orienté
    (positif = favorable) : vert si favorable, ambre jusqu'à -5 %, rouge au-delà.
    """

    def appliquer():
        from Spotfire.Dxp.Application.Visuals.ConditionalColoring import (
            ConditionValue,
            IntervalMode,
        )

        axe.Coloring.Clear()
        regle = axe.Coloring.AddContinuousColorRule()
        regle.IntervalMode = IntervalMode.Gradient
        if binaire:
            # rouge sous zéro, vert au-dessus, sans nuance
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(-0.000001), ROUGE)
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(0.000001), VERT)
        elif tranche:
            regle.Breakpoints.Add(
                ConditionValue.CreateLiteral(-SEUIL_ALERTE - 0.000001), ROUGE
            )
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(-SEUIL_ALERTE), AMBRE)
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(-0.000001), AMBRE)
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(0.000001), VERT)
        else:
            regle.Breakpoints.Add(ConditionValue.MinValue, ROUGE)
            regle.Breakpoints.Add(ConditionValue.CreateLiteral(0.0), NEUTRE)
            regle.Breakpoints.Add(ConditionValue.MaxValue, VERT)

    essayer("dégradé", appliquer)


def carte_de_chaleur(tableau):
    """Tableau croisé : fond des cellules du rouge au vert selon la valeur."""

    class Porteur(object):
        pass

    def appliquer():
        porteur = Porteur()
        porteur.Coloring = tableau.Colorings.AddNew("Écart")
        degrade(porteur)
        tableau.Colorings.DefaultNumericReference = porteur.Coloring

    essayer("carte de chaleur " + tableau.Title, appliquer)


def cascade_coloree(cascade, expression):
    """Cascade : contributions favorables en vert, défavorables en rouge."""
    essayer(
        "cascade couleur " + cascade.Title,
        lambda: setattr(cascade.ColorAxis, "Expression", expression),
    )
    degrade(cascade.ColorAxis, binaire=True)
    # la légende n'afficherait que les deux seuils de couleur
    sans_legende(cascade)


def largeur_libelles(tableau, largeur):
    """Tableau croisé : élargit la colonne des libellés pour ne plus les tronquer."""

    def regler():
        largeurs = tableau.RowHeaderWidths
        try:
            for rang in range(largeurs.Count):
                largeurs[rang] = largeur
        except Exception as erreur:
            raise ValueError(
                "%s ; membres : %s"
                % (erreur, [n for n in dir(largeurs) if not n.startswith("_")])
            )

    essayer("largeur libellés " + tableau.Title, regler)


def surligner_lignes(tableau, libelles, couleur):
    """Tableau croisé dont les lignes sont des mesures : fond de couleur sur certaines."""

    def regler():
        from Spotfire.Dxp.Application.Visuals import CategoryKey

        fond = tableau.Colorings.AddNew("Soldes")
        fond.AddExpressionRule("1 = 1", couleur)
        for libelle in libelles:
            tableau.Colorings.AddMapping(CategoryKey(libelle), fond)

    essayer("lignes surlignées " + tableau.Title, regler)


def format_souple():
    """Milliers séparés, décimale seulement si elle existe : « 74 216 », « -4,7 »."""
    from Spotfire.Dxp.Data import DataType
    from Spotfire.Dxp.Data.Formatters import NumberFormatCategory

    f = DataType.Real.CreateLocalizedFormatter()
    f.Category = NumberFormatCategory.Custom
    f.FormatString = "#,##0.#"
    return f


def legende_large(visuel, largeur=200):
    """Légende assez large pour le nom complet des BU."""
    essayer(
        "légende large " + visuel.Title,
        lambda: setattr(visuel.Legend, "Width", largeur),
    )


def police_axe(visuel, facteur):
    """Réduit la police de l'axe des catégories pour afficher tous les libellés."""

    def regler():
        actuelle = visuel.XAxis.Scale.FontMetadata
        visuel.XAxis.Scale.FontMetadata = actuelle.WithSize(
            actuelle.Size * facteur, actuelle.Unit
        )

    essayer("police axe " + visuel.Title, regler)


def format_reel(decimales):
    from Spotfire.Dxp.Data import DataType
    from Spotfire.Dxp.Data.Formatters import NumberFormatCategory

    f = DataType.Real.CreateLocalizedFormatter()
    f.Category = NumberFormatCategory.Number
    f.DecimalDigits = decimales
    f.GroupSeparatorEnabled = True
    return f


def format_ecart(suffixe):
    """Écart signé avec son unité : « ▲ +1,1 % », « ▼ -1,8 pts »."""
    from Spotfire.Dxp.Data import DataType
    from Spotfire.Dxp.Data.Formatters import NumberFormatCategory

    f = DataType.Real.CreateLocalizedFormatter()
    f.Category = NumberFormatCategory.Custom
    # triangle de hausse ou de baisse, signe, une décimale, unité
    f.FormatString = "'▲' +0.0 '%s';'▼' -0.0 '%s';0.0 '%s'" % (
        suffixe,
        suffixe,
        suffixe,
    )
    return f


def format_unite(unite):
    """Valeur avec son unité accolée : « 74,2 M€ », « 29,5 % »."""
    from Spotfire.Dxp.Data import DataType
    from Spotfire.Dxp.Data.Formatters import NumberFormatCategory

    f = DataType.Real.CreateLocalizedFormatter()
    f.Category = NumberFormatCategory.Custom
    f.FormatString = "0.0 '%s'" % unite
    return f


def format_entier():
    from Spotfire.Dxp.Data import DataType
    from Spotfire.Dxp.Data.Formatters import NumberFormatCategory

    f = DataType.Integer.CreateLocalizedFormatter()
    f.Category = NumberFormatCategory.Number
    essayer("entier sans décimale", lambda: setattr(f, "DecimalDigits", 0))
    f.GroupSeparatorEnabled = True
    return f


def format_axe(visuel, decimales=0):
    """Axe des valeurs : séparateur de milliers, pas de décimales inutiles."""
    essayer(
        "format axe " + visuel.Title,
        lambda: setattr(
            visuel.YAxis.Scale.Formatting, "RealFormatter", format_reel(decimales)
        ),
    )


def tableau_soigne(tableau, largeur=95):
    """Tableau croisé : milliers séparés, taux à une décimale, colonnes lisibles."""
    essayer(
        "format réels " + tableau.Title,
        lambda: setattr(tableau.Formatting, "RealFormatter", format_reel(1)),
    )
    essayer(
        "format entiers " + tableau.Title,
        lambda: setattr(tableau.Formatting, "IntegerFormatter", format_entier()),
    )
    essayer("largeur " + tableau.Title, lambda: setattr(tableau, "CellWidth", largeur))
    essayer(
        "sélecteurs " + tableau.Title,
        lambda: setattr(tableau, "ShowAxisSelectors", False),
    )


def etiquettes(barres):
    """Affiche la valeur sur chaque barre ou segment."""

    def poser():
        import System
        from Spotfire.Dxp.Application.Visuals import LabelVisibility

        barres.LabelVisibility = LabelVisibility.All
        # l'énumération change de nom selon les versions : on la prend sur la propriété
        genre = type(barres.SegmentLabelInformationType)
        noms = list(System.Enum.GetNames(genre))
        if "Value" not in noms:
            raise ValueError("types d'étiquette disponibles : %s" % noms)
        barres.SegmentLabelInformationType = getattr(genre, "Value")
        barres.LabelSegments = True
        barres.LabelCompleteBar = False

    essayer("étiquettes " + barres.Title, poser)


def couleur_unique(visuel, couleur):
    essayer(
        "couleur " + visuel.Title,
        lambda: setattr(visuel.ColorAxis.Coloring, "DefaultColor", couleur),
    )


def totaux(tableau, ligne_total=True):
    """Tableau croisé : une ligne de total en bas (ou aucune), jamais de colonnes de total."""
    essayer("total bas", lambda: setattr(tableau, "ShowColumnGrandTotal", ligne_total))
    essayer("total droite", lambda: setattr(tableau, "ShowRowGrandTotal", False))


def ordre_personnalise(nom_table, colonne, valeurs):
    """Ordre d'affichage métier d'une colonne (au lieu de l'ordre alphabétique)."""
    from System import Object
    from System.Collections.Generic import List

    liste = List[Object]()
    for valeur in valeurs:
        liste.Add(valeur)
    essayer(
        "ordre " + colonne,
        lambda: table(nom_table).Columns[colonne].Properties.SetCustomSortOrder(liste),
    )


def disposer(page, lignes):
    """lignes = [(hauteur, [(visuel, largeur), ...]), ...] : une ligne par bande horizontale."""
    plan = LayoutDefinition()
    plan.BeginStackedSection()
    for hauteur, visuels in lignes:
        plan.BeginSideBySideSection(hauteur)
        for visuel, largeur in visuels:
            plan.Add(visuel.Visual, largeur)
        plan.EndSection()
    plan.EndSection()
    page.ApplyLayout(plan)


# la table issue du classeur Excel porte un nom à rallonge : on la renomme
for t in Document.Data.Tables:
    if t.Name.endswith("ventes_agences"):
        t.Name = "ventes_agences"


def dernier_mois_clos():
    """Dernier mois de 2026 présent dans la table bfr (elle ne contient que des mois clos)."""
    from Spotfire.Dxp.Data import DataValueCursor

    bfr = table("bfr")
    exercice = DataValueCursor.CreateFormatted(bfr.Columns["Exercice"])
    mois = DataValueCursor.CreateFormatted(bfr.Columns["Mois"])
    dernier = 0
    for _ in bfr.GetRows(exercice, mois):
        if exercice.CurrentValue == "2026":
            dernier = max(dernier, int(mois.CurrentValue))
    return dernier


DERNIER_MOIS = dernier_mois_clos()

# Les mois s'affichent par leur nom, dans l'ordre du calendrier.
MOIS = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]
AXE_MOIS = "<[Période]>"


def ajouter_periode(nom_table):
    colonnes = table(nom_table).Columns
    if not colonnes.Contains("Période"):
        cas = " ".join('when %d then "%s"' % (i + 1, m) for i, m in enumerate(MOIS))
        colonnes.AddCalculatedColumn("Période", "case [Mois] " + cas + " end")
    ordre_personnalise(nom_table, "Période", MOIS)


for nom_table in ("ventes", "compte_resultat", "bfr", "tresorerie"):
    essayer("période " + nom_table, lambda n=nom_table: ajouter_periode(n))

# ménage : colonnes de travail laissées par un essai de lignes alternées
for t in Document.Data.Tables:
    for colonne in [c for c in t.Columns if c.Name.startswith("Rang ")]:
        essayer("ménage " + colonne.Name, lambda c=colonne, tb=t: tb.Columns.Remove(c))

anciennes = list(Document.Pages)
for fichier in ONGLETS:
    exec(io.open(DOSSIER + fichier, encoding="utf-8").read(), globals())
for page in anciennes:
    Document.Pages.Remove(page)
# tant que les anciens onglets existaient, Spotfire a suffixé les nouveaux titres : « (2) »
for page in Document.Pages:
    page.Title = re.sub(r" \(\d+\)$", "", page.Title)
Document.ActivePageReference = Document.Pages[0]


# Sélections dynamiques : un clic sur un mois (ou une BU) recalcule toute la page.
# 1. les tables mensuelles sont reliées par le mois, la sélection passe de l'une à l'autre
def relier(gauche, droite):
    relations = Document.Data.Relations
    for relation in relations:
        if set([relation.LeftTable.Name, relation.RightTable.Name]) == set(
            [gauche, droite]
        ):
            return
    relations.Add(
        table(gauche),
        table(droite),
        "[%s].[Mois] = [%s].[Mois]" % (gauche, droite),
    )


# en étoile autour des ventes : Spotfire refuse les relations qui forment une boucle
for autre in ("compte_resultat", "resultat_lignes", "bfr", "tresorerie"):
    essayer("relation ventes - " + autre, lambda a=autre: relier("ventes", a))


# 2. chaque visuel se limite aux lignes sélectionnées ; sans sélection, il montre tout
def suivre_la_selection(donnees):
    import System

    marquage = Document.Data.Markings.DefaultMarkingReference
    # un visuel créé par script ne sélectionne rien tant qu'on ne lui donne pas de marquage
    donnees.MarkingReference = marquage
    if not donnees.Filterings.Contains(marquage):
        donnees.Filterings.Add(marquage)
    # l'énumération n'est pas importable par son nom : on la prend sur la propriété
    genre = type(donnees.LimitingMarkingsEmptyBehavior)
    noms = list(System.Enum.GetNames(genre))
    if "ShowAll" not in noms:
        raise ValueError("comportements disponibles : %s" % noms)
    donnees.LimitingMarkingsEmptyBehavior = getattr(genre, "ShowAll")


def blocs_de_donnees(visuel):
    """Un visuel simple a un bloc de données ; une rangée de tuiles en a un par tuile."""
    from Spotfire.Dxp.Application.Visuals import KpiChart, Visualization
    from Spotfire.Dxp.Application.Visuals.Maps import MapChart

    # la carte reste entière : limitée à la sélection, elle perd ses marqueurs
    # dès que rien n'est sélectionné. Elle sert à choisir des agences (voir plus bas).
    if visuel.As[MapChart]() is not None:
        return []
    tuiles = visuel.As[KpiChart]()
    if tuiles is not None:
        return [contenu.Visualization.Data for contenu in tuiles.KpiCollection]
    simple = visuel.As[Visualization]()
    return [simple.Data] if simple is not None else []


for page in Document.Pages:
    for visuel in page.Visuals:
        essayer(
            "sélection " + visuel.Title,
            lambda v=visuel: [suivre_la_selection(d) for d in blocs_de_donnees(v)],
        )


# la carte sélectionne des agences sans se limiter elle-même
def carte_selectionne(visuel):
    from Spotfire.Dxp.Application.Visuals import Visualization
    from Spotfire.Dxp.Application.Visuals.Maps import MapChart

    if visuel.As[MapChart]() is None:
        return
    donnees = visuel.As[Visualization]().Data
    donnees.MarkingReference = Document.Data.Markings.DefaultMarkingReference


for page in Document.Pages:
    for visuel in page.Visuals:
        essayer("sélection carte", lambda v=visuel: carte_selectionne(v))

# ménage : première version de la table dépivotée du compte de résultat
if Document.Data.Tables.Contains("resultat_versions"):
    essayer(
        "ménage resultat_versions",
        lambda: Document.Data.Tables.Remove(table("resultat_versions")),
    )

# sécurité par région, appliquée en dernier sur tous les visuels
exec(io.open(DOSSIER + "06_securite.py", encoding="utf-8").read(), globals())

journal_avertissements = io.open(DOSSIER + "_avertissements.log", "w", encoding="utf-8")
journal_avertissements.write("\n".join(AVERTISSEMENTS) or "Aucun avertissement")
journal_avertissements.close()
